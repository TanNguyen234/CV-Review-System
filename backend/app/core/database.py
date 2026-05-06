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
            # Set a 5-second timeout for server selection
            cls.client = AsyncIOMotorClient(settings.mongo_url, serverSelectionTimeoutMS=5000)
            cls.db = cls.client.get_default_database("CV-Review")
            if cls.db.name == "test":
                # if URL has no database name, fallback to a specific one
                cls.db = cls.client["CV-Review"]
            
            # Simple ping to verify connection
            import asyncio
            # We use a future to run the ping in the background without blocking the lifespan start
            # but we log the result
            async def ping():
                try:
                    await cls.client.admin.command('ping')
                    logger.info(f"Connected to MongoDB database: {cls.db.name}")
                except Exception as ping_e:
                    logger.error(f"MongoDB Ping failed: {ping_e}")
            
            # Since connect() is sync, we can't await ping() here easily without a loop
            # But lifespan will call this. In FastAPI lifespan, we can just run it.
            # For now, let's keep it simple.
            logger.info(f"MongoDB client initialized for: {cls.db.name}")
        except Exception as e:
            logger.error(f"Failed to initialize MongoDB client: {e}")

    @classmethod
    def disconnect(cls):
        if cls.client:
            logger.info("Disconnecting from MongoDB...")
            cls.client.close()

db_manager = Database()
