from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import text
from app.models.documents import Document as DocumentModel
from app.schemas.tender_request import Document as DocumentSchema
from app.crud.errors import log_tender_error
from app.core.logging_config import logger


async def save_documents(db: AsyncSession, tender_id: str, documents: list[DocumentSchema], tender_url: str | None = None) -> bool:
    all_saved = True
    for doc in documents:
        if not doc.url or not doc.file_name:
            file_name = doc.file_name or "unknown"
            url = doc.url or tender_url or "unknown"
            error_msg = "Отсутствует url или file_name"
            logger.error(error_msg)
            await log_tender_error(db, tender_id, f"{error_msg}: {url}")
            db_doc = DocumentModel(
                tender_id=tender_id,
                file_name=file_name,
                url=url,
                storage_location="original",
                status="error"
            )
            all_saved = False
        else:
            # Проверяем, существует ли документ
            result = await db.execute(
                select(DocumentModel).filter(DocumentModel.tender_id == tender_id, DocumentModel.file_name == doc.file_name)
            )
            existing_doc = result.scalars().first()
            if existing_doc:
                # Обновляем существующий документ
                existing_doc.url = doc.url
                existing_doc.storage_location = "s3"
                existing_doc.status = "downloaded"
                db.add(existing_doc)
            else:
                # Создаём новый документ
                db_doc = DocumentModel(
                    tender_id=tender_id,
                    file_name=doc.file_name,
                    url=doc.url,
                    storage_location="s3",
                    status="downloaded"
                )
                db.add(db_doc)

        try:
            await db.commit()
            if not existing_doc:
                await db.refresh(db_doc)
        except IntegrityError as e:
            await db.rollback()
            error_msg = f"Документ с tender_id={tender_id} и file_name={doc.file_name} уже существует: {doc.url}"
            logger.error(error_msg)
            await log_tender_error(db, tender_id, error_msg)
            all_saved = False
            continue
        except Exception as e:
            await db.rollback()
            logger.error(f"Unexpected error saving document for tender {tender_id}: {str(e)}")
            all_saved = False
            continue

    return all_saved


async def get_documents_by_tender_id(db: AsyncSession, tender_id: str) -> list[DocumentSchema]:
    result = await db.execute(select(DocumentModel).filter(DocumentModel.tender_id == tender_id))
    docs = result.scalars().all()
    return [DocumentSchema(file_name=doc.file_name, url=doc.url) for doc in docs]


async def log_download_error(db: AsyncSession, tender_id: str, file_url: str, reason: str) -> None:
    await log_tender_error(db, tender_id, f"{reason}: {file_url}")


async def update_document_url(db: AsyncSession, tender_id: str, file_name: str, new_url: str) -> bool:
    """Обновляет URL документа в базе данных."""
    try:
        # Проверяем, существует ли документ
        result = await db.execute(
            select(DocumentModel).filter(DocumentModel.tender_id == tender_id, DocumentModel.file_name == file_name)
        )
        existing_doc = result.scalars().first()
        if existing_doc:
            existing_doc.url = new_url
            existing_doc.storage_location = "s3"
            existing_doc.status = "downloaded"
            db.add(existing_doc)
            await db.commit()
            logger.info(f"Updated URL for document {file_name} of tender {tender_id} to {new_url}")
            return True
        else:
            logger.warning(f"No document found to update for tender {tender_id} with file_name {file_name}")
            return False
    except Exception as e:
        logger.error(f"Error updating document URL for tender {tender_id}, file {file_name}: {str(e)}")
        await db.rollback()
        return False