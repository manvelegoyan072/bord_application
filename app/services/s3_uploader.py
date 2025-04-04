import aiohttp
import aiobotocore.session
import re
from app.core.logging_config import logger
from app.core.config import settings


async def upload_to_s3(url: str, file_name: str, tender_id: str) -> str | None:

    logger.info(f"Starting upload for file {file_name} from {url} for tender {tender_id}")
    try:
        async with aiohttp.ClientSession() as session:

            if "drive.google.com" in url:

                file_id_match = re.search(r'file/d/([a-zA-Z0-9_-]+)/', url)
                if not file_id_match:
                    logger.error(f"Не удалось извлечь ID файла из Google Drive URL: {url}")
                    return None

                file_id = file_id_match.group(1)
                download_url = f"https://drive.google.com/uc?export=download&id={file_id}"

                async with session.get(download_url) as response:
                    if response.status != 200:
                        logger.error(f"Ошибка при скачивании с Google Drive {url}: HTTP {response.status}")
                        return None

                    #
                    content_type = response.headers.get('Content-Type', '')
                    if 'text/html' in content_type:
                        html_content = await response.text()
                        token_match = re.search(r'confirm=([0-9A-Za-z]+)', html_content)
                        if token_match:
                            confirm_token = token_match.group(1)
                            download_url = f"https://drive.google.com/uc?export=download&id={file_id}&confirm={confirm_token}"
                            async with session.get(download_url) as response:
                                if response.status != 200:
                                    logger.error(
                                        f"Ошибка после подтверждения Google Drive {url}: HTTP {response.status}")
                                    return None
                                content = await response.read()
                        else:
                            logger.error(f"Не удалось найти confirmation token для Google Drive {url}")
                            return None
                    else:
                        content = await response.read()
            else:
                # Обычный URL
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to download {url}: HTTP {response.status}")
                        return None
                    content = await response.read()

            if content is None:
                logger.error(f"Не удалось скачать содержимое файла из {url}")
                return None

        # Формируем ключ для S3
        s3_key = f"tenders/{tender_id}/{file_name}"
        session = aiobotocore.session.get_session()

        # Создаём клиента S3
        async with session.create_client(
                "s3",
                endpoint_url=settings.S3_ENDPOINT_URL,
                aws_access_key_id=settings.S3_ACCESS_KEY,
                aws_secret_access_key=settings.S3_SECRET_KEY,
                region_name=settings.S3_REGION
        ) as s3_client:
            await s3_client.put_object(
                Bucket=settings.S3_BUCKET_NAME,
                Key=s3_key,
                Body=content
            )

        s3_url = f"{settings.S3_ENDPOINT_URL}/{settings.S3_BUCKET_NAME}/{s3_key}"
        logger.info(f"Successfully uploaded {file_name} to Yandex S3: {s3_url}")
        return s3_url
    except Exception as e:
        logger.error(f"Error uploading {file_name} for tender {tender_id}: {str(e)}")
        return None


