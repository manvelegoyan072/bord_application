from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import text
from app.schemas.tender_request import TenderRequest, Document
from app.crud.errors import log_tender_error
from app.services.checklist_validator import validate_tender, validate_documents
from app.services.notifications import send_telegram_alert
from app.core.logging_config import logger
from app.services.s3_uploader import upload_to_s3
from app.services.selenium_scraper import scrape_documents
from app.services.filter_service import apply_filters
from app.services.ai_service import process_with_ai
from app.services.bitrix_service import export_to_bitrix
from app.services.tender_state_machine import TenderStateMachine
from app.models.tenders import Tender
from app.crud.documents import save_documents
from app.db.database import AsyncSessionLocal as async_session
import aiohttp
from aiohttp.client_exceptions import ClientConnectorCertificateError, ClientError

async def update_tender_state(db: AsyncSession, tender: Tender, state: str, tender_id: str):
    tender.state = state
    logger.debug(f"Updating tender state for {tender_id} to {state}")
    db.add(tender)
    await db.commit()
    await db.refresh(tender)

async def process_and_save_tender(tender_data: TenderRequest, type_name: str) -> Tender | None:
    async with async_session() as db:
        tender_id = tender_data.id
        logger.info(f"Starting processing tender {tender_id} of type {type_name}, state: {tender_data.state}")

        result = await db.execute(
            select(Tender)
            .options(joinedload(Tender.docs), joinedload(Tender.lots))
            .filter(Tender.external_id == tender_id)
        )
        db_tender = result.scalars().first()
        if not db_tender:
            logger.error(f"Tender {tender_id} not found in database")
            return None

        sm = TenderStateMachine(db_tender, tender_id)

        try:
            # Валидация
            await sm.start_validating()
            await update_tender_state(db, db_tender, sm.state, tender_id)
            errors = validate_tender(tender_data)
            doc_errors = validate_documents(tender_data.docs)
            if errors or doc_errors:
                await sm.fail_validation()
                await update_tender_state(db, db_tender, sm.state, tender_id)
                error_message = "; ".join(errors + doc_errors)
                logger.error(f"Validation failed for tender {tender_id}: {error_message}")
                await log_tender_error(db, tender_id, error_message)
                await send_telegram_alert(db_tender, f"Ошибка валидации: {error_message}")
                return None

            # Загрузка документов
            await sm.fetch_documents()
            await update_tender_state(db, db_tender, sm.state, tender_id)
            updated_docs = []
            seen_urls = set()

            async with aiohttp.ClientSession() as session:
                for doc in tender_data.docs:
                    if doc.url in seen_urls:
                        logger.warning(f"Skipping duplicate document URL: {doc.url}")
                        continue
                    seen_urls.add(doc.url)
                    logger.debug(f"Processing document {doc.file_name} with URL {doc.url}")

                    try:
                        async with session.head(doc.url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=10)) as head_response:
                            if head_response.status == 200:
                                new_url = await upload_to_s3(doc.url, doc.file_name, tender_id)
                                if new_url:
                                    updated_docs.append(Document(file_name=doc.file_name, url=new_url))
                                    logger.info(f"Successfully uploaded {doc.file_name} to S3: {new_url}")
                                    # Обновляем URL в базе данных с использованием text()
                                    await db.execute(
                                        text("UPDATE documents SET url = :new_url WHERE tender_id = :tender_id AND file_name = :file_name"),
                                        {"new_url": new_url, "tender_id": tender_id, "file_name": doc.file_name}
                                    )
                                    await db.commit()
                                else:
                                    logger.error(f"Failed to upload document {doc.file_name} from {doc.url}")
                                    raise Exception("Upload failed despite accessible URL")
                            else:
                                logger.warning(f"Document URL {doc.url} returned status {head_response.status}, attempting scraping")
                                raise Exception(f"HEAD request failed with status {head_response.status}")

                    except (ClientConnectorCertificateError, ClientError, Exception) as e:
                        logger.error(f"Failed to fetch document {doc.file_name} from {doc.url}: {str(e)}")
                        await sm.documents_not_found()
                        await update_tender_state(db, db_tender, sm.state, tender_id)

                        await sm.start_scraping()
                        await update_tender_state(db, db_tender, sm.state, tender_id)
                        logger.info(f"Attempting scraping via kontur_link: {db_tender.kontur_link}")
                        scraped_docs = await scrape_documents(db_tender, db)
                        if scraped_docs:
                            if await save_documents(db, tender_id, scraped_docs, db_tender.kontur_link):
                                updated_docs.extend(scraped_docs)
                                await sm.finish_scraping()
                                await update_tender_state(db, db_tender, sm.state, tender_id)
                                logger.info(f"Scraping via kontur_link successful, {len(scraped_docs)} documents saved for tender {tender_id}")
                            else:
                                logger.error(f"Failed to save scraped documents from kontur_link for tender {tender_id}")
                                await sm.fail_scraping()
                                await update_tender_state(db, db_tender, sm.state, tender_id)
                                await send_telegram_alert(db_tender, "Не удалось сохранить документы, скачанные через kontur_link")
                                return None
                        else:
                            logger.info(f"Scraping via kontur_link failed, attempting via etp_url: {db_tender.etp_url}")
                            original_kontur_link = db_tender.kontur_link
                            db_tender.kontur_link = db_tender.etp_url
                            scraped_docs = await scrape_documents(db_tender, db)
                            db_tender.kontur_link = original_kontur_link
                            if scraped_docs:
                                if await save_documents(db, tender_id, scraped_docs, db_tender.etp_url):
                                    updated_docs.extend(scraped_docs)
                                    await sm.finish_scraping()
                                    await update_tender_state(db, db_tender, sm.state, tender_id)
                                    logger.info(f"Scraping via etp_url successful, {len(scraped_docs)} documents saved for tender {tender_id}")
                                else:
                                    logger.error(f"Failed to save scraped documents from etp_url for tender {tender_id}")
                                    await sm.fail_scraping()
                                    await update_tender_state(db, db_tender, sm.state, tender_id)
                                    await send_telegram_alert(db_tender, "Не удалось сохранить документы, скачанные через etp_url")
                                    return None
                            else:
                                logger.error(f"Scraping failed for tender {tender_id} using both kontur_link and etp_url")
                                await sm.fail_scraping()
                                await update_tender_state(db, db_tender, sm.state, tender_id)
                                safe_message = f"Не удалось скачать документы через kontur_link ({db_tender.kontur_link}) и etp_url ({db_tender.etp_url})"
                                await send_telegram_alert(db_tender, safe_message)
                                return None

            if updated_docs:
                await sm.save_documents()
                await update_tender_state(db, db_tender, sm.state, tender_id)
            else:
                logger.error(f"No valid documents processed for tender {tender_id}")
                await sm.documents_not_found()
                await update_tender_state(db, db_tender, sm.state, tender_id)
                safe_message = f"Не удалось обработать документы для тендера {tender_id}"
                await send_telegram_alert(db_tender, safe_message)
                return None

            # Фильтрация
            await sm.start_filtering()
            await update_tender_state(db, db_tender, sm.state, tender_id)
            if not await apply_filters(db_tender, tender_id, db):
                await sm.reject_after_filtering()
                await update_tender_state(db, db_tender, sm.state, tender_id)
                logger.info(f"Tender {tender_id} rejected after filtering")
                return db_tender

            # AI-обработка
            await sm.start_ai()
            await update_tender_state(db, db_tender, sm.state, tender_id)
            if not await process_with_ai(db_tender, db):
                await sm.reject_after_ai()
                await update_tender_state(db, db_tender, sm.state, tender_id)
                logger.info(f"Tender {tender_id} rejected after AI processing")
                return db_tender

            # Экспорт
            await sm.prepare_export()
            await update_tender_state(db, db_tender, sm.state, tender_id)
            await sm.start_exporting()
            await update_tender_state(db, db_tender, sm.state, tender_id)
            if await export_to_bitrix(db_tender, db):
                await sm.complete()
                await update_tender_state(db, db_tender, sm.state, tender_id)
                logger.info(f"Tender {tender_id} successfully completed")
            else:
                await sm.fail_export()
                await update_tender_state(db, db_tender, sm.state, tender_id)
                logger.error(f"Export failed for tender {tender_id}")
                await send_telegram_alert(db_tender, "Ошибка экспорта в Bitrix")
                return db_tender

            logger.info(f"Tender {tender_id} processing finished, state: {db_tender.state}")
            return db_tender

        except Exception as e:
            logger.error(f"Error processing tender {tender_id}: {str(e)}")
            await sm.encounter_error()
            await update_tender_state(db, db_tender, sm.state, tender_id)
            safe_message = f"Ошибка обработки тендера {tender_id}: {str(e)}"
            await send_telegram_alert(db_tender, safe_message)
            raise