import asyncio
import asyncpg
from alembic.config import Config
from alembic import command
from app.core.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def wait_for_db():
    retries = 5
    db_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    for i in range(retries):
        try:
            conn = await asyncpg.connect(db_url)
            await conn.close()
            logger.info("Database is ready!")
            return True
        except Exception as e:
            logger.error(f"Waiting for database... Attempt {i+1}/{retries}: {e}")
            await asyncio.sleep(2)
    logger.error("Failed to connect to database after retries")
    raise Exception("Database connection failed")

def apply_migrations():
    try:
        asyncio.run(wait_for_db())
        logger.info("Starting migrations...")
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
        logger.info(f"Using DATABASE_URL: {settings.DATABASE_URL}")
        logger.info("Running Alembic upgrade to head...")
        command.upgrade(alembic_cfg, "head", sql=False)  # sql=False для реального выполнения
        logger.info("Migrations applied!")
    except Exception as e:
        logger.error(f"Failed to apply migrations: {e}")
        raise

if __name__ == "__main__":
    apply_migrations()