import logging
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

logger = logging.getLogger(__name__)

class Database:
    client: AsyncIOMotorClient = None
    db = None

    @classmethod
    def connect(cls):
        if not settings.mongo_url:
            logger.warning("MONGO_URL not set in environment variables.")
            return
        
        try:
            logger.info("Connecting to MongoDB...")
            cls.client = AsyncIOMotorClient(settings.mongo_url)
            cls.db = cls.client.get_default_database("cv_review_db")
            if cls.db.name == "test":
                # if URL has no database name, fallback to a specific one
                cls.db = cls.client["cv_review_db"]
            logger.info(f"Connected to MongoDB database: {cls.db.name}")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")

    @classmethod
    def disconnect(cls):
        if cls.client:
            logger.info("Disconnecting from MongoDB...")
            cls.client.close()

db_manager = Database()
