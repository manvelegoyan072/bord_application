import os
import asyncio
from typing import List
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, WebDriverException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from app.schemas.tender_request import Document
from app.models.tenders import Tender
from app.services.s3_uploader import upload_to_s3
from app.core.logging_config import logger
from sqlalchemy.ext.asyncio import AsyncSession

# Папка для хранения драйвера
DRIVER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "drivers")
os.makedirs(DRIVER_DIR, exist_ok=True)


def get_local_driver_path() -> str:

    driver_path = os.path.join(DRIVER_DIR, "chromedriver" + (".exe" if os.name == "nt" else ""))

    if not os.path.exists(driver_path):
        logger.info("ChromeDriver not found locally, downloading to drivers folder...")
        # Скачиваем драйвер один раз и сохраняем в DRIVER_DIR
        driver_path = ChromeDriverManager(path=DRIVER_DIR).install()
        logger.info(f"ChromeDriver downloaded to: {driver_path}")
    else:
        logger.debug(f"Using existing ChromeDriver at: {driver_path}")

    return driver_path


async def scrape_documents(tender: Tender, db: AsyncSession) -> List[Document] | None:
    logger.info(f"Starting document scraping for tender {tender.external_id} using kontur_link: {tender.kontur_link}")

    if not tender.kontur_link:
        logger.error(f"No kontur_link provided for tender {tender.external_id}")
        return None

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    download_dir = os.getenv("DOWNLOAD_DIR", "/tmp")
    options.add_experimental_option("prefs", {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    })

    loop = asyncio.get_event_loop()
    driver = None
    try:

        driver_path = await loop.run_in_executor(None, get_local_driver_path)
        service = Service(executable_path=driver_path)
        driver = await loop.run_in_executor(None, lambda: webdriver.Chrome(service=service, options=options))
        scraped_docs = []


        await loop.run_in_executor(None, driver.get, tender.kontur_link)
        wait = WebDriverWait(driver, 15)
        await asyncio.sleep(5)

        # Ждём появления элементов с PDF-ссылками
        document_links = await loop.run_in_executor(
            None,
            lambda: wait.until(EC.presence_of_all_elements_located((By.XPATH, "//a[contains(@href, '.pdf')]")))
        )
        if not document_links:
            logger.warning(f"No PDF links found on {tender.kontur_link}")
            return None

        for link in document_links:
            doc_url = await loop.run_in_executor(None, link.get_attribute, "href")
            doc_name = doc_url.split("/")[-1] or f"document_{len(scraped_docs) + 1}.pdf"
            logger.info(f"Found document link: {doc_url}, name: {doc_name}")

            try:
                # Скачиваем файл через клик
                await loop.run_in_executor(None, link.click)
                await asyncio.sleep(5)

                file_path = os.path.join(download_dir, doc_name)
                max_wait = 15
                wait_time = 0
                while not os.path.exists(file_path) and wait_time < max_wait:
                    await asyncio.sleep(1)
                    wait_time += 1

                if os.path.exists(file_path):
                    s3_url = await upload_to_s3(file_path, doc_name, tender.external_id)
                    if s3_url:
                        scraped_docs.append(Document(file_name=doc_name, url=s3_url))
                        os.remove(file_path)
                        logger.info(f"Successfully uploaded {doc_name} to S3: {s3_url}")
                    else:
                        logger.error(f"Failed to upload {doc_name} to S3")
                else:
                    # Прямая загрузка через URL, если клик не сработал
                    s3_url = await upload_to_s3(doc_url, doc_name, tender.external_id)
                    if s3_url:
                        scraped_docs.append(Document(file_name=doc_name, url=s3_url))
                        logger.info(f"Directly uploaded {doc_name} to S3: {s3_url}")
                    else:
                        logger.error(f"Failed to download or upload {doc_name} from {doc_url}")
            except Exception as e:
                logger.error(f"Failed to process document {doc_name} from {doc_url}: {str(e)}")

        if not scraped_docs:
            logger.warning(f"No documents successfully scraped from {tender.kontur_link}")
            return None

        logger.info(f"Successfully scraped {len(scraped_docs)} documents for tender {tender.external_id}")
        return scraped_docs

    except TimeoutException:
        logger.error(f"Timeout waiting for PDF links on {tender.kontur_link}")
        return None
    except WebDriverException as e:
        logger.error(f"Selenium WebDriver error for tender {tender.external_id}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during scraping for tender {tender.external_id}: {str(e)}")
        return None
    finally:
        if driver:
            await loop.run_in_executor(None, driver.quit)
            logger.debug(f"WebDriver closed for tender {tender.external_id}")