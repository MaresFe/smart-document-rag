from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.document import Document
from app.schemas.document import DocumentRead
from app.services.dev_user import DEV_USER_ID, get_or_create_dev_user
from app.services.document_upload import save_upload_file


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
        status="uploaded",
    )

    db.add(document)
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