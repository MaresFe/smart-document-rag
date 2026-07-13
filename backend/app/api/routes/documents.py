from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.schemas.document import DocumentRead
from app.schemas.document_chunk import DocumentChunkRead
from app.services.chunking import chunk_text
from app.services.dev_user import DEV_USER_ID, get_or_create_dev_user
from app.services.document_upload import save_upload_file
from app.services.text_extraction import TextExtractionError, extract_text_from_document


router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


@router.post(
    "",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
)
def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    get_or_create_dev_user(db)

    stored_filename, storage_path, file_size, file_type = save_upload_file(file)

    document = Document(
        user_id=DEV_USER_ID,
        original_filename=file.filename,
        stored_filename=stored_filename,
        file_type=file_type,
        mime_type=file.content_type,
        file_size=file_size,
        storage_path=storage_path,
        status="processing",
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    try:
        extracted_text = extract_text_from_document(
            file_type=document.file_type,
            storage_path=document.storage_path,
        )

        chunks = chunk_text(extracted_text)

        if not chunks:
            raise TextExtractionError("No extractable text found in document.")

        document_chunks = [
            DocumentChunk(
                document_id=document.id,
                chunk_index=index,
                content=chunk,
                source_metadata={
                    "file_type": document.file_type,
                    "original_filename": document.original_filename,
                },
            )
            for index, chunk in enumerate(chunks)
        ]

        db.add_all(document_chunks)

        document.status = "ready"
        document.error_message = None

        db.commit()
        db.refresh(document)

    except TextExtractionError as error:
        document.status = "failed"
        document.error_message = str(error)

        db.commit()
        db.refresh(document)

    return document


@router.get("", response_model=list[DocumentRead])
def list_documents(db: Session = Depends(get_db)):
    statement = select(Document).order_by(Document.created_at.desc())
    documents = db.execute(statement).scalars().all()
    return documents


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(
    document_id: UUID,
    db: Session = Depends(get_db),
):
    document = db.get(Document, document_id)

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    return document


@router.get("/{document_id}/chunks", response_model=list[DocumentChunkRead])
def list_document_chunks(
    document_id: UUID,
    db: Session = Depends(get_db),
):
    document = db.get(Document, document_id)

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    statement = (
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
    )

    chunks = db.execute(statement).scalars().all()

    return chunks