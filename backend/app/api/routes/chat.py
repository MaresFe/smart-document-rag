import logging
from time import perf_counter
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.db.session import get_db
from app.models.chat import ChatMessage, ChatSession
from app.models.chat_session_document import (
    ChatSessionDocument,
)
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.message_source import MessageSource
from app.models.user import User
from app.schemas.chat import (
    ChatMessageCreate,
    ChatMessageRead,
    ChatResponse,
    ChatSessionCreate,
    ChatSessionDocumentCreate,
    ChatSessionDocumentRead,
    ChatSessionRead,
    ChatSessionUpdate,
    ChatSourceRead,
)
from app.services.embedding import EmbeddingError
from app.services.answer_validation import (
    FIXED_NOT_FOUND_ANSWER,
)
from app.services.llm import LLMError, generate_answer
from app.services.retrieval import (
    RetrievedChunk,
    retrieve_relevant_chunks,
)

performance_logger = logging.getLogger(
    "uvicorn.error",
)

router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
)


def get_owned_chat_session(
    db: Session,
    session_id: UUID,
    user_id: UUID,
) -> ChatSession:
    statement = select(ChatSession).where(
        ChatSession.id == session_id,
        ChatSession.user_id == user_id,
    )

    chat_session = db.scalar(statement)

    if chat_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found.",
        )

    return chat_session


def build_retrieval_based_answer(
    question: str,
    retrieved_chunks: list[RetrievedChunk],
) -> str:
    if not retrieved_chunks:
        return FIXED_NOT_FOUND_ANSWER

    source_sections: list[str] = []

    for index, result in enumerate(
        retrieved_chunks,
        start=1,
    ):
        content = result.content.strip()

        if len(content) > 700:
            content = f"{content[:700]}..."

        source_sections.append(
            f"[Kaynak {index} - "
            f"{result.original_filename}]\n{content}"
        )

    return (
        "Yanıt modeli şu anda kullanılamıyor. "
        "Soruyla en alakalı belge parçaları aşağıdadır.\n\n"
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
    current_user: User = Depends(get_current_user),
) -> ChatSession:
    normalized_title = (
        request.title.strip()
        if request.title
        else None
    )

    chat_session = ChatSession(
        user_id=current_user.id,
        title=normalized_title or "Yeni sohbet",
    )

    db.add(chat_session)
    db.commit()
    db.refresh(chat_session)

    return chat_session


@router.get(
    "/sessions",
    response_model=list[ChatSessionRead],
)
def list_chat_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ChatSession]:
    statement = (
        select(ChatSession)
        .where(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.created_at.desc())
    )

    return list(db.scalars(statement).all())


@router.patch(
    "/sessions/{session_id}",
    response_model=ChatSessionRead,
)
def update_chat_session(
    session_id: UUID,
    request: ChatSessionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatSession:
    chat_session = get_owned_chat_session(
        db=db,
        session_id=session_id,
        user_id=current_user.id,
    )

    normalized_title = request.title.strip()

    if not normalized_title:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Chat session title cannot be empty.",
        )

    chat_session.title = normalized_title

    db.commit()
    db.refresh(chat_session)

    return chat_session


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_chat_session(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    chat_session = get_owned_chat_session(
        db=db,
        session_id=session_id,
        user_id=current_user.id,
    )

    db.delete(chat_session)
    db.commit()

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )


@router.get(
    "/sessions/{session_id}/documents",
    response_model=list[ChatSessionDocumentRead],
)
def list_chat_session_documents(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ChatSessionDocument]:
    get_owned_chat_session(
        db=db,
        session_id=session_id,
        user_id=current_user.id,
    )

    statement = (
        select(ChatSessionDocument)
        .join(
            Document,
            Document.id
            == ChatSessionDocument.document_id,
        )
        .where(
            ChatSessionDocument.session_id == session_id,
            Document.user_id == current_user.id,
        )
        .order_by(ChatSessionDocument.created_at)
    )

    return list(db.scalars(statement).all())


@router.post(
    "/sessions/{session_id}/documents",
    response_model=list[ChatSessionDocumentRead],
)
def attach_documents_to_chat_session(
    session_id: UUID,
    request: ChatSessionDocumentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ChatSessionDocument]:
    get_owned_chat_session(
        db=db,
        session_id=session_id,
        user_id=current_user.id,
    )

    unique_document_ids = list(
        dict.fromkeys(request.document_ids),
    )

    if unique_document_ids:
        document_statement = select(Document).where(
            Document.id.in_(unique_document_ids),
            Document.user_id == current_user.id,
        )

        documents = list(
            db.scalars(document_statement).all(),
        )
    else:
        documents = []

    found_document_ids = {
        document.id
        for document in documents
    }

    if len(found_document_ids) != len(unique_document_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more documents were not found.",
        )

    existing_statement = select(
        ChatSessionDocument,
    ).where(
        ChatSessionDocument.session_id == session_id,
    )

    existing_links = list(
        db.scalars(existing_statement).all(),
    )

    existing_document_ids = {
        link.document_id
        for link in existing_links
    }

    requested_document_ids = set(
        unique_document_ids,
    )

    for link in existing_links:
        if link.document_id not in requested_document_ids:
            db.delete(link)

    new_links = [
        ChatSessionDocument(
            session_id=session_id,
            document_id=document_id,
        )
        for document_id in unique_document_ids
        if document_id not in existing_document_ids
    ]

    db.add_all(new_links)
    db.commit()

    final_statement = (
        select(ChatSessionDocument)
        .join(
            Document,
            Document.id
            == ChatSessionDocument.document_id,
        )
        .where(
            ChatSessionDocument.session_id == session_id,
            Document.user_id == current_user.id,
        )
        .order_by(ChatSessionDocument.created_at)
    )

    return list(db.scalars(final_statement).all())


@router.get(
    "/sessions/{session_id}/messages",
    response_model=list[ChatMessageRead],
)
def list_chat_messages(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ChatMessage]:
    get_owned_chat_session(
        db=db,
        session_id=session_id,
        user_id=current_user.id,
    )

    statement = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    )

    return list(db.scalars(statement).all())


@router.get(
    "/sessions/{session_id}/messages/"
    "{message_id}/sources",
    response_model=list[ChatSourceRead],
)
def list_chat_message_sources(
    session_id: UUID,
    message_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ChatSourceRead]:
    get_owned_chat_session(
        db=db,
        session_id=session_id,
        user_id=current_user.id,
    )

    message_statement = select(ChatMessage).where(
        ChatMessage.id == message_id,
        ChatMessage.session_id == session_id,
    )

    message = db.scalar(message_statement)

    if message is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat message not found.",
        )

    source_statement = (
        select(
            MessageSource,
            DocumentChunk,
            Document.original_filename,
        )
        .join(
            DocumentChunk,
            DocumentChunk.id == MessageSource.chunk_id,
        )
        .join(
            Document,
            Document.id == DocumentChunk.document_id,
        )
        .where(
            MessageSource.message_id == message_id,
            Document.user_id == current_user.id,
        )
        .order_by(
            MessageSource.similarity_score.desc(),
        )
    )

    rows = db.execute(source_statement).all()

    return [
        ChatSourceRead(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            similarity_score=source.similarity_score,
            original_filename=original_filename,
        )
        for source, chunk, original_filename in rows
    ]


@router.post(
    "/sessions/{session_id}/messages",
    response_model=ChatResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_chat_message(
    session_id: UUID,
    request: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    total_started = perf_counter()
    preparation_started = total_started

    chat_session = get_owned_chat_session(
        db=db,
        session_id=session_id,
        user_id=current_user.id,
    )

    normalized_content = request.content.strip()

    if not normalized_content:
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=(
                "Message content cannot be empty."
            ),
        )

    user_message = ChatMessage(
        session_id=chat_session.id,
        role="user",
        content=normalized_content,
    )

    db.add(user_message)
    db.flush()

    linked_documents_statement = (
        select(Document.id)
        .join(
            ChatSessionDocument,
            ChatSessionDocument.document_id
            == Document.id,
        )
        .where(
            ChatSessionDocument.session_id
            == chat_session.id,
            Document.user_id == current_user.id,
            Document.status == "ready",
        )
    )

    linked_document_ids = list(
        db.scalars(
            linked_documents_statement,
        ).all(),
    )

    preparation_ms = (
        perf_counter() - preparation_started
    ) * 1000

    retrieval_started = perf_counter()

    try:
        retrieved_chunks = (
            retrieve_relevant_chunks(
                db=db,
                query=normalized_content,
                user_id=current_user.id,
                limit=5,
                document_ids=linked_document_ids,
            )
        )
    except EmbeddingError as error:
        retrieval_ms = (
            perf_counter() - retrieval_started
        ) * 1000

        performance_logger.warning(
            "RAG request failed | "
            "session_id=%s | "
            "stage=retrieval | "
            "elapsed_ms=%.2f | "
            "error_type=%s",
            session_id,
            retrieval_ms,
            type(error).__name__,
        )

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    retrieval_ms = (
        perf_counter() - retrieval_started
    ) * 1000

    llm_started = perf_counter()
    used_fallback = False

    if retrieved_chunks:
        try:
            assistant_content = generate_answer(
                question=normalized_content,
                retrieved_chunks=retrieved_chunks,
            )
        except LLMError as error:
            used_fallback = True

            performance_logger.warning(
                "RAG LLM fallback | "
                "session_id=%s | "
                "error_type=%s",
                session_id,
                type(error).__name__,
            )

            assistant_content = (
                build_retrieval_based_answer(
                    question=normalized_content,
                    retrieved_chunks=(
                        retrieved_chunks
                    ),
                )
            )
    else:
        used_fallback = True

        assistant_content = (
            build_retrieval_based_answer(
                question=normalized_content,
                retrieved_chunks=[],
            )
        )

    llm_ms = (
        perf_counter() - llm_started
    ) * 1000

    persistence_started = perf_counter()

    assistant_message = ChatMessage(
        session_id=chat_session.id,
        role="assistant",
        content=assistant_content,
    )

    db.add(assistant_message)
    db.flush()

    answer_uses_sources = (
        assistant_content.strip().casefold()
        != FIXED_NOT_FOUND_ANSWER.casefold()
    )

    source_chunks = (
        retrieved_chunks
        if answer_uses_sources
        else []
    )

    message_sources = [
        MessageSource(
            message_id=assistant_message.id,
            chunk_id=result.chunk_id,
            similarity_score=(
                result.similarity_score
            ),
        )
        for result in source_chunks
    ]

    db.add_all(message_sources)

    db.commit()
    db.refresh(user_message)
    db.refresh(assistant_message)

    persistence_ms = (
        perf_counter() - persistence_started
    ) * 1000

    sources = [
        ChatSourceRead(
            chunk_id=result.chunk_id,
            document_id=result.document_id,
            chunk_index=result.chunk_index,
            content=result.content,
            similarity_score=(
                result.similarity_score
            ),
            original_filename=(
                result.original_filename
            ),
        )
        for result in source_chunks
    ]

    total_ms = (
        perf_counter() - total_started
    ) * 1000

    performance_logger.info(
        "RAG request timing | "
        "session_id=%s | "
        "linked_documents=%d | "
        "sources=%d | "
        "preparation_ms=%.2f | "
        "retrieval_ms=%.2f | "
        "llm_ms=%.2f | "
        "persistence_ms=%.2f | "
        "total_ms=%.2f | "
        "fallback=%s",
        session_id,
        len(linked_document_ids),
        len(sources),
        preparation_ms,
        retrieval_ms,
        llm_ms,
        persistence_ms,
        total_ms,
        used_fallback,
    )

    return ChatResponse(
        user_message=user_message,
        assistant_message=assistant_message,
        sources=sources,
    )
