import asyncio
import aiohttp
import aiobotocore.session
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.tenders import Tender
from app.models.ai_checks import AICheck
from app.core.logging_config import logger
from app.core.config import settings
import json
import os

SUPPORTED_FORMATS = {".txt", ".doc", ".docx", ".pdf", ".xlsx", ".xls", ".html"}

async def process_with_ai(tender: Tender, db: AsyncSession) -> bool:
    tender_id = tender.external_id
    logger.info(f"Starting AI processing for tender {tender_id}")

    if not tender.docs:
        logger.error(f"No documents found for tender {tender_id}")
        return False

    doc = tender.docs[0]
    doc_url = doc.url
    file_name = doc.file_name.lower()
    if not doc_url or not any(file_name.endswith(fmt) for fmt in SUPPORTED_FORMATS):
        logger.error(f"No suitable document for tender {tender_id} (URL: {doc_url}, File: {file_name})")
        return False

    # Отправляем файл в AI и получаем task_id
    task_id = await send_to_ai_parse(doc_url)
    if not task_id:
        logger.error(f"Failed to send tender {tender_id} to AI")
        return False

    # Сохраняем task_id в ai_checks с начальным статусом
    ai_check = AICheck(
        tender_id=tender_id,
        ai_status="PENDING",
        task_id=task_id,
        ai_response=None
    )
    db.add(ai_check)
    await db.commit()
    await db.refresh(ai_check)
    logger.info(f"Saved task_id {task_id} for tender {tender_id} in ai_checks")

    # Опрашиваем статус задачи
    task_result = await poll_task(task_id)
    if not task_result:
        logger.error(f"Polling failed for tender {tender_id}")
        ai_check.ai_status = "FAILED"
        await db.commit()
        return False

    status = task_result.get("status")
    result = task_result.get("result", "No data")
    logger.info(f"AI result for tender {tender_id}: status={status}, result={result}")

    # Обновляем запись в ai_checks с результатом
    ai_check.ai_status = status
    ai_check.ai_response = json.dumps(result, ensure_ascii=False)
    await db.commit()

    # Проверяем, принят ли тендер
    is_accepted = False
    if status == "SUCCESS" and isinstance(result, dict) and "parameters" in result:
        is_accepted = any(param.get("accepted_for_recommendation", False) for param in result.get("parameters", []))

    return is_accepted

async def send_to_ai_parse(doc_url: str) -> str | None:
    if "storage.yandexcloud.net" in doc_url:
        s3_key = doc_url.replace(f"{settings.S3_ENDPOINT_URL}/{settings.S3_BUCKET_NAME}/", "")
        session = aiobotocore.session.get_session()
        async with session.create_client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION
        ) as s3_client:
            try:
                response = await s3_client.get_object(Bucket=settings.S3_BUCKET_NAME, Key=s3_key)
                file_content = await response['Body'].read()
                filename = s3_key.split('/')[-1]
            except Exception as e:
                logger.error(f"Failed to download from S3 {doc_url}: {str(e)}")
                return None
    else:
        async with aiohttp.ClientSession() as session:
            async with session.get(doc_url) as response:
                if response.status != 200:
                    logger.error(f"Failed to download file {doc_url}: {response.status}")
                    return None
                file_content = await response.read()
                filename = doc_url.split('/')[-1]

    async with aiohttp.ClientSession() as session:
        try:
            headers = {"Authorization": f"Bearer {settings.AI_API_TOKEN}"}
            form_data = aiohttp.FormData()
            form_data.add_field('files', file_content, filename=filename)
            form_data.add_field('details', '')

            async with session.post(f"{settings.AI_API_BASE_URL}/parse", headers=headers, data=form_data) as resp:
                if resp.status in (200, 202):
                    data = await resp.json()
                    task_id = data.get("task_id")
                    if task_id:
                        logger.info(f"File sent to AI, task_id: {task_id}, status: {resp.status}")
                        return task_id
                    else:
                        logger.error(f"AI response missing task_id: {await resp.text()}")
                        return None
                else:
                    logger.error(f"Failed to send to AI: {resp.status}, response: {await resp.text()}")
                    return None
        except Exception as e:
            logger.error(f"Error sending file to AI: {e}")
            return None

async def poll_task(task_id: str, timeout: int = 600, interval: int = 10) -> dict | None:
    start_time = asyncio.get_event_loop().time()
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                url = f"{settings.AI_API_BASE_URL}/task_status/{task_id}"
                headers = {"Authorization": f"Bearer {settings.AI_API_TOKEN}"}
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        task_data = await resp.json()
                        status = task_data.get("status")
                        if status in ["SUCCESS", "REJECTED", "ERROR"]:
                            return task_data
                        elif status == "IN PROGRESS":
                            logger.info(f"Task {task_id} still in progress")
                    else:
                        logger.error(f"Polling: unexpected status code {resp.status}")
                        return None
            except Exception as e:
                logger.error(f"Error polling task {task_id}: {e}")
                return None

            await asyncio.sleep(interval)
            if asyncio.get_event_loop().time() - start_time > timeout:
                logger.error(f"Task {task_id} polling timed out")
                return {"status": "TIMEOUT", "result": "Task polling timed out"}