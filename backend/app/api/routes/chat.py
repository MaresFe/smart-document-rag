from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.chat import ChatMessage, ChatSession
from app.models.message_source import MessageSource
from app.schemas.chat import (
    ChatMessageCreate,
    ChatMessageRead,
    ChatResponse,
    ChatSessionCreate,
    ChatSessionRead,
    ChatSourceRead,
)
from app.services.dev_user import DEV_USER_ID, get_or_create_dev_user
from app.services.embedding import EmbeddingError
from app.services.retrieval import RetrievedChunk, retrieve_relevant_chunks
from app.services.llm import LLMError, generate_answer


router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
)


def build_retrieval_based_answer(
    question: str,
    retrieved_chunks: list[RetrievedChunk],
) -> str:
    if not retrieved_chunks:
        return (
            "Bu soruyla ilgili yeterli doküman parçası bulunamadı. "
            "Daha farklı bir soru sormayı veya daha ilgili bir doküman yüklemeyi deneyebilirsin."
        )

    source_sections: list[str] = []

    for index, result in enumerate(retrieved_chunks, start=1):
        content = result.content.strip()

        if len(content) > 700:
            content = f"{content[:700]}..."

        source_sections.append(
            f"[Kaynak {index} - {result.original_filename}]\n{content}"
        )

    return (
        "Bu aşamada LLM cevap üretimi henüz eklenmedi. "
        "Aşağıda soruyla en alakalı bulunan doküman parçalarını getiriyorum.\n\n"
        f"Soru: {question}\n\n"
        + "\n\n".join(source_sections)
    )


@router.post(
    "/sessions",
    response_model=ChatSessionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_chat_session(
    request: ChatSessionCreate,
    db: Session = Depends(get_db),
):
    get_or_create_dev_user(db)

    session = ChatSession(
        user_id=DEV_USER_ID,
        title=request.title,
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    return session


@router.get("/sessions", response_model=list[ChatSessionRead])
def list_chat_sessions(db: Session = Depends(get_db)):
    statement = (
        select(ChatSession)
        .where(ChatSession.user_id == DEV_USER_ID)
        .order_by(ChatSession.created_at.desc())
    )

    sessions = db.execute(statement).scalars().all()

    return sessions


@router.get(
    "/sessions/{session_id}/messages",
    response_model=list[ChatMessageRead],
)
def list_chat_messages(
    session_id: UUID,
    db: Session = Depends(get_db),
):
    session = db.get(ChatSession, session_id)

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found.",
        )

    statement = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    )

    messages = db.execute(statement).scalars().all()

    return messages


@router.post(
    "/sessions/{session_id}/messages",
    response_model=ChatResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_chat_message(
    session_id: UUID,
    request: ChatMessageCreate,
    db: Session = Depends(get_db),
):
    session = db.get(ChatSession, session_id)

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found.",
        )

    user_message = ChatMessage(
        session_id=session.id,
        role="user",
        content=request.content,
    )

    db.add(user_message)
    db.flush()

    try:
        retrieved_chunks = retrieve_relevant_chunks(
            db=db,
            query=request.content,
            limit=5,
        )
    except EmbeddingError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    try:
        assistant_content = generate_answer(
            question=request.content,
            retrieved_chunks=retrieved_chunks,
        )
    except LLMError:
        assistant_content = build_retrieval_based_answer(
            question=request.content,
            retrieved_chunks=retrieved_chunks,
    )

    assistant_message = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=assistant_content,
    )

    db.add(assistant_message)
    db.flush()

    message_sources = [
        MessageSource(
            message_id=assistant_message.id,
            chunk_id=result.chunk_id,
            similarity_score=result.similarity_score,
        )
        for result in retrieved_chunks
    ]

    db.add_all(message_sources)

    db.commit()
    db.refresh(user_message)
    db.refresh(assistant_message)

    sources = [
        ChatSourceRead(
            chunk_id=result.chunk_id,
            document_id=result.document_id,
            chunk_index=result.chunk_index,
            content=result.content,
            similarity_score=result.similarity_score,
            original_filename=result.original_filename,
        )
        for result in retrieved_chunks
    ]

    return ChatResponse(
        user_message=user_message,
        assistant_message=assistant_message,
        sources=sources,
    )