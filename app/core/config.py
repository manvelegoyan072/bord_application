from os import getenv
from dotenv import load_dotenv

load_dotenv()

class Config:

    ALLOWED_ORIGINS: list = getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")


    POSTGRES_USER: str = getenv("POSTGRES_USER")
    POSTGRES_PASSWORD: str = getenv("POSTGRES_PASSWORD")
    POSTGRES_DB: str = getenv("POSTGRES_DB")
    POSTGRES_PORT: str=  getenv("POSTGRES_PORT")

    @property
    def DATABASE_URL(self) -> str:
        return getenv(
            "DATABASE_URL",
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@db:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Bitrix24
    BITRIX_WEBHOOK_URL: str = getenv("BITRIX_WEBHOOK_URL")
    KEPLER_API_TOKEN: str = getenv("KEPLER_API_TOKEN")

    # AI-сервис
    AI_API_BASE_URL: str = getenv("AI_API_BASE_URL")
    AI_API_TOKEN: str = getenv("AI_API_TOKEN")

    # S3-хранилище (Yandex Object Storage)
    S3_ENDPOINT_URL: str = getenv("S3_ENDPOINT_URL")
    S3_BUCKET_NAME: str = getenv("S3_BUCKET_NAME")
    S3_REGION: str = getenv("S3_REGION")
    S3_ACCESS_KEY: str = getenv("S3_ACCESS_KEY")
    S3_SECRET_KEY: str = getenv("S3_SECRET_KEY")

    # Telegram-уведомления
    TELEGRAM_BOT_TOKEN: str = getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID: str = getenv("TELEGRAM_CHAT_ID")

    # Порт приложения
    APP_PORT: int = int(getenv("APP_PORT", "8000"))

    def validate(self) -> None:
        """Проверяет наличие обязательных переменных окружения."""
        required_vars = {
            "BITRIX_WEBHOOK_URL": self.BITRIX_WEBHOOK_URL,
            "KEPLER_API_TOKEN": self.KEPLER_API_TOKEN,
            "S3_ACCESS_KEY": self.S3_ACCESS_KEY,
            "S3_SECRET_KEY": self.S3_SECRET_KEY,
            "TELEGRAM_BOT_TOKEN": self.TELEGRAM_BOT_TOKEN,
            "TELEGRAM_CHAT_ID": self.TELEGRAM_CHAT_ID,
        }
        missing_vars = [key for key, value in required_vars.items() if not value]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

settings = Config()
settings.validate()