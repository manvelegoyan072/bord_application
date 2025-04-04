import re
from urllib.parse import urlparse
from app.schemas.tender_request import TenderRequest, Document

REQUIRED_FORMATS = ["pdf", "docx", "zip", "7z", "xls", "xlsx"]
MAX_FILE_SIZE_MB = 10

def validate_tender(tender: TenderRequest) -> list[str]:

    errors = []


    if not tender.id:
        errors.append("Отсутствует ID заявки")
    if not tender.notification_number:
        errors.append("Отсутствует номер закупки")
    if not tender.title:
        errors.append("Отсутствует название")
    if not tender.publication_date:
        errors.append("Отсутствует дата публикации")
    if not tender.application_deadline:
        errors.append("Отсутствует дедлайн подачи")


    organizer = tender.organizer or {}
    if not organizer.get("fullName"):
        errors.append("Отсутствует полное название организатора")
    if not is_valid_inn(organizer.get("inn", "")):
        errors.append("Некорректный ИНН организатора")

    if "kpp" in organizer and not is_valid_kpp(organizer.get("kpp", "")):
        errors.append("Некорректный КПП организатора")


    if "email" in organizer and not is_valid_email(organizer.get("email", "")):
        errors.append("Некорректный email организатора")
    if "phone" in organizer and not is_valid_phone(organizer.get("phone", "")):
        errors.append("Некорректный телефон организатора")

    return errors

def validate_documents(documents: list[Document]) -> list[str]:

    errors = []

    if not documents:
        errors.append("Нет документов")

    for doc in documents:
        if not doc.file_name:
            errors.append(f"Документ без имени: {doc.url}")
        elif not is_valid_format(doc.file_name):
            errors.append(f"Неподдерживаемый формат: {doc.file_name}")

        if not is_valid_url(doc.url):
            errors.append(f"Некорректный URL: {doc.url}")

    return errors

def is_valid_inn(inn: str) -> bool:
    """Проверка ИНН (10 или 12 цифр)"""
    return bool(re.fullmatch(r"\d{10}|\d{12}", str(inn)))

def is_valid_kpp(kpp: str) -> bool:
    """Проверка КПП (9 цифр)"""
    return bool(re.fullmatch(r"\d{9}", str(kpp)))

def is_valid_email(email: str) -> bool:
    """Проверка email-формата"""
    return bool(re.fullmatch(r"[^@]+@[^@]+\.[^@]+", email))

def is_valid_phone(phone: str) -> bool:
    """Проверка телефона (+7 (999) 123-45-67)"""
    return bool(re.fullmatch(r"^\+?\d{1,3}\s?\(?\d{3}\)?[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}$", phone))

def is_valid_format(file_name: str) -> bool:
    """Проверка расширения файла"""
    return file_name.split(".")[-1].lower() in REQUIRED_FORMATS

def is_valid_url(url: str) -> bool:
    """Проверка, что URL валидный"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False