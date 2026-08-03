from pathlib import Path
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.db.session import get_db
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.user import User
from app.schemas.document import DocumentRead
from app.schemas.document_chunk import DocumentChunkRead
from app.services.chunking import chunk_text
from app.services.document_upload import save_upload_file
from app.services.embedding import (
    EmbeddingError,
    create_passage_embeddings,
)
from app.services.text_extraction import (
    TextExtractionError,
    extract_text_from_document,
)


router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


def get_owned_document(
    db: Session,
    document_id: UUID,
    user_id: UUID,
) -> Document:
    statement = select(Document).where(
        Document.id == document_id,
        Document.user_id == user_id,
    )

    document = db.scalar(statement)

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    return document


def remove_document_and_file(
    db: Session,
    document: Document,
) -> None:
    storage_path = Path(
        document.storage_path,
    )

    db.delete(document)
    db.commit()

    try:
        storage_path.unlink(
            missing_ok=True,
        )
    except OSError:
        pass


def get_extraction_error_detail(
    file_type: str,
    error: TextExtractionError,
) -> str:
    error_message = str(error).strip()

    if file_type == "pdf":
        detailed_pdf_error_markers = (
            "OCR işlemi",
            "OCR motoru",
            "OCR görüntü",
            "OCR ile işlenemedi",
            "OCR gerektiren",
            "zaman sınırını",
            "sayfa sayısı",
            "görüntü boyutu",
            "okunamadı veya bozuk",
        )

        if any(
            marker in error_message
            for marker
            in detailed_pdf_error_markers
        ):
            return error_message

        return (
            "PDF dosyasında metin katmanı "
            "veya OCR ile okunabilir içerik "
            "bulunamadı."
        )

    error_messages = {
        "docx": (
            "DOCX dosyası işlenebilir "
            "metin veya tablo içermiyor."
        ),
        "xlsx": (
            "XLSX dosyası işlenebilir "
            "çalışma sayfası verisi içermiyor."
        ),
        "csv": (
            "CSV dosyası okunamadı veya "
            "işlenebilir satır içermiyor."
        ),
        "txt": (
            "TXT dosyası işlenebilir "
            "metin içermiyor."
        ),
    }

    return error_messages.get(
        file_type,
        error_message
        or (
            "Belgeden işlenebilir metin "
            "çıkarılamadı."
        ),
    )


@router.post(
    "",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
)
def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user,
    ),
) -> Document:
    (
        stored_filename,
        storage_path,
        file_size,
        file_type,
    ) = save_upload_file(file)

    document = Document(
        user_id=current_user.id,
        original_filename=(
            file.filename
            or stored_filename
        ),
        stored_filename=stored_filename,
        file_type=file_type,
        mime_type=file.content_type,
        file_size=file_size,
        storage_path=storage_path,
        status="processing",
    )

    try:
        db.add(document)
        db.commit()
        db.refresh(document)

    except Exception:
        db.rollback()

        Path(storage_path).unlink(
            missing_ok=True,
        )

        raise

    try:
        extracted_text = (
            extract_text_from_document(
                file_type=document.file_type,
                storage_path=(
                    document.storage_path
                ),
            )
        )

        chunks = chunk_text(
            extracted_text,
        )

        if not chunks:
            raise TextExtractionError(
                "Belgede çıkarılabilir "
                "metin bulunamadı.",
            )

        embeddings = (
            create_passage_embeddings(
                chunks,
            )
        )

        document_chunks = [
            DocumentChunk(
                document_id=document.id,
                chunk_index=index,
                content=chunk,
                embedding=embeddings[index],
                source_metadata={
                    "file_type": (
                        document.file_type
                    ),
                    "original_filename": (
                        document
                        .original_filename
                    ),
                },
            )
            for index, chunk
            in enumerate(chunks)
        ]

        db.add_all(
            document_chunks,
        )

        document.status = "ready"
        document.error_message = None

        db.commit()
        db.refresh(document)

    except TextExtractionError as error:
        error_detail = (
            get_extraction_error_detail(
                file_type=(
                    document.file_type
                ),
                error=error,
            )
        )

        remove_document_and_file(
            db=db,
            document=document,
        )

        raise HTTPException(
            status_code=(
                status
                .HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=error_detail,
        ) from error

    except EmbeddingError:
        document.status = "failed"
        document.error_message = (
            "Belge metni çıkarıldı ancak "
            "anlamsal indeks oluşturulamadı."
        )

        db.commit()
        db.refresh(document)

    return document


@router.get(
    "",
    response_model=list[DocumentRead],
)
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user,
    ),
) -> list[Document]:
    statement = (
        select(Document)
        .where(
            Document.user_id
            == current_user.id,
        )
        .order_by(
            Document.created_at.desc(),
        )
    )

    return list(
        db.scalars(statement).all(),
    )


@router.get(
    "/{document_id}",
    response_model=DocumentRead,
)
def get_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user,
    ),
) -> Document:
    return get_owned_document(
        db=db,
        document_id=document_id,
        user_id=current_user.id,
    )


@router.get(
    "/{document_id}/chunks",
    response_model=list[DocumentChunkRead],
)
def list_document_chunks(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user,
    ),
) -> list[DocumentChunk]:
    get_owned_document(
        db=db,
        document_id=document_id,
        user_id=current_user.id,
    )

    statement = (
        select(DocumentChunk)
        .where(
            DocumentChunk.document_id
            == document_id,
        )
        .order_by(
            DocumentChunk.chunk_index,
        )
    )

    return list(
        db.scalars(statement).all(),
    )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user,
    ),
) -> Response:
    document = get_owned_document(
        db=db,
        document_id=document_id,
        user_id=current_user.id,
    )

    remove_document_and_file(
        db=db,
        document=document,
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )