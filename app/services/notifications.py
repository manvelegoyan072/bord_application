import aiohttp
from app.core.logging_config import logger
from app.models.tenders import Tender
from app.core.config import settings  # Импортируем конфигурацию

async def send_telegram_alert(tender: Tender, message: str) -> None:
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        logger.error("Telegram credentials not configured")
        return

    full_message = (
        f"Тендер: {tender.external_id}\n"
        f"Название: {tender.title}\n"
        f"Состояние: {tender.state}\n"
        f"Сообщение: {message}\n"
        f"Kontur Link: {tender.kontur_link}"
    )

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": settings.TELEGRAM_CHAT_ID,
        "text": full_message,
        "parse_mode": "Markdown"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    logger.error(f"Failed to send Telegram alert: HTTP {response.status}, {await response.text()}")
                else:
                    logger.info(f"Telegram alert sent for tender {tender.external_id}: {message}")
    except Exception as e:
        logger.error(f"Error sending Telegram alert for tender {tender.external_id}: {str(e)}")