import aiohttp
import aiobotocore.session
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.tenders import Tender
from app.services.notifications import send_telegram_alert
from app.core.logging_config import logger
from app.core.config import settings

async def upload_file_to_bitrix(session: aiohttp.ClientSession, file_url: str, tender_id: str) -> str | None:

    if "storage.yandexcloud.net" not in file_url:
        logger.error(f"Unsupported file URL for Bitrix upload: {file_url}")
        return None

    s3_key = file_url.replace(f"{settings.S3_ENDPOINT_URL}/{settings.S3_BUCKET_NAME}/", "")
    s3_session = aiobotocore.session.get_session()
    async with s3_session.create_client(
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
            logger.error(f"Failed to download from S3 {file_url}: {str(e)}")
            return None

    form_data = aiohttp.FormData()
    form_data.add_field("file", file_content, filename=filename)
    async with session.post(
        f"{settings.BITRIX_WEBHOOK_URL}/disk.file.upload", data=form_data
    ) as resp:
        if resp.status == 200:
            result = await resp.json()
            file_id = result.get("result", {}).get("ID")
            logger.info(f"File {filename} uploaded to Bitrix with ID {file_id}")
            return file_id
        else:
            logger.error(f"Failed to upload file to Bitrix: {resp.status}, {await resp.text()}")
            return None

async def update_user_field(session: aiohttp.ClientSession, field_id: str, enum_values: list[str]):

    payload = {
        "ID": field_id,
        "fields": {
            "ENUM": [{"VALUE": value} for value in enum_values]
        }
    }
    async with session.post(
        f"{settings.BITRIX_WEBHOOK_URL}/crm.userfield.update", json=payload
    ) as resp:
        if resp.status == 200:
            logger.info(f"Updated user field {field_id} with values {enum_values}")
        else:
            logger.error(f"Failed to update user field {field_id}: {resp.status}, {await resp.text()}")

async def export_to_bitrix(tender: Tender, db: AsyncSession) -> bool:

    headers = {"Content-Type": "application/json"}
    async with aiohttp.ClientSession() as session:
        await update_user_field(session, "UF_CRM_1742608808760", ["Оплата после поставки"])
        await update_user_field(session, "UF_CRM_1742608851091", ["30 дней"])

        file_id = None
        if tender.docs and tender.docs[0].url:
            file_id = await upload_file_to_bitrix(session, tender.docs[0].url, tender.external_id)

        payload = {
            "fields": {
                "TITLE": f"{tender.lots[0].title if tender.lots else tender.title} (ID: {tender.external_id})",
                "ASSIGNED_BY_ID": 9,
                "SOURCE_ID": "BIDZAAR",
                "SOURCE_DESCRIPTION": tender.etp_url or "",
                "OPPORTUNascopy link | edit linkOPPORTUNITY": str(tender.initial_price),
                "CURRENCY_ID": tender.currency,
                "COMPANY_TITLE": tender.organizer.get("shortName", ""),
                "PHONE": [{"VALUE": tender.organizer.get("phone", ""), "VALUE_TYPE": "WORK"}],
                "EMAIL": [{"VALUE": tender.organizer.get("email", ""), "VALUE_TYPE": "WORK"}],
                "COMMENTS": (
                    f"Тип: {tender.type}\n"
                    f"Номер уведомления: {tender.notification_number}\n"
                    f"Тип уведомления: {tender.notification_type}\n"
                    f"Метод выбора: {tender.selection_method}\n"
                    f"SMP: {tender.smp}\n"
                    f"Дата публикации: {tender.publication_date.isoformat() if tender.publication_date else ''}"
                ),
                "UF_CRM_1742603751016": tender.lots[0].title if tender.lots else tender.title,
                "UF_CRM_1742606680844": file_id if file_id else "",
                "UF_CRM_1742606760239": tender.etp_url or "",
                "UF_CRM_1742609850193": tender.organizer.get("fullName", ""),
                "UF_CRM_1742609875440": tender.external_id,
                "UF_CRM_1742609910653": tender.notification_number or "",
                "UF_CRM_1742609934994": tender.lots[0].title if tender.lots else tender.title,
                "UF_CRM_1742609963686": tender.selection_method or "Тендер",
                "UF_CRM_1742609998740": tender.notification_type or "",
                "UF_CRM_1742610026724": str(tender.initial_price),
                "UF_CRM_1742610077432": tender.etp_url or "",
                "UF_CRM_1742610126567": tender.kontur_link or "",
                "UF_CRM_1742610167102": tender.application_deadline.isoformat() if tender.application_deadline else "",
                "UF_CRM_1742610221983": tender.last_modified.isoformat() if tender.last_modified else "",
                "UF_CRM_1742610256352": tender.lots[0].delivery_place if tender.lots else "",
                "UF_CRM_1742610279807": tender.organizer.get("inn", ""),
                "UF_CRM_1742610403956": file_id if file_id else "",
                "UF_CRM_1742610442197": tender.docs[0].url if tender.docs else "",
                "UF_CRM_1742610493435": tender.organizer.get("phone", ""),
                "UF_CRM_1742610518824": (
                    f"{tender.lots[0].title if tender.lots else tender.title}, "
                    f"сумма: {tender.initial_price} {tender.currency}, "
                    f"доставка: {tender.lots[0].delivery_place if tender.lots else ''}, "
                    f"срок: {tender.lots[0].delivery_term if tender.lots else ''}, "
                    f"оплата: {tender.lots[0].payment_term if tender.lots else ''}"
                ),
                "UF_CRM_1742608808760": tender.lots[0].payment_term if tender.lots else "",
                "UF_CRM_1742608851091": tender.lots[0].delivery_term if tender.lots else ""
            }
        }

        async with session.post(f"{settings.BITRIX_WEBHOOK_URL}/crm.lead.add.json", json=payload, headers=headers) as resp:
            if resp.status == 200:
                bitrix_id = (await resp.json()).get("result")
                logger.info(f"Tender {tender.external_id} exported to Bitrix with ID {bitrix_id}")
                return bool(bitrix_id)
            else:
                logger.error(f"Failed to export tender {tender.external_id} to Bitrix: {resp.status}")
                await send_telegram_alert(tender, f"Ошибка экспорта в Bitrix для заявки {tender.external_id}: {resp.status}")
                return False