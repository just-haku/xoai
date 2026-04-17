import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from xoai.config import settings
from xoai.auth.service import hash_password

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_admin")

async def seed():
    logger.info("Connecting to MongoDB...")
    client = AsyncIOMotorClient(settings.mongo_uri)
    db_name = settings.mongo_uri.split('/')[-1].split('?')[0] or "xoai"
    db = client[db_name]

    logger.info("Seeding Super-Admin: kuro_admin")
    admin_doc = {
        "username": "kuro_admin",
        "email": None,
        "password_hash": hash_password("00491E4C@haku"),
        "name": "KURO",
        "role": "admin",
        "status": "approved",
        "email_verified": True,
        "quota_used_bytes": 0,
        "lang": "EN",
    }
    
    await db.users.insert_one(admin_doc)
    await db.users.create_index("email", unique=True, sparse=True)
    await db.users.create_index("username", unique=True, sparse=True)
    await db.settings.create_index("key", unique=True)
    
    logger.info("✅ Super-Admin seeded successfully.")
    client.close()

if __name__ == "__main__":
    asyncio.run(seed())
