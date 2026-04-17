import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from xoai.config import settings
from xoai.auth.service import hash_password

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("reset_db")

async def reset_db():
    logger.info("Connecting to MongoDB...")
    client = AsyncIOMotorClient(settings.mongo_uri)
    db_name = settings.mongo_uri.split('/')[-1].split('?')[0] or "xoai"
    db = client[db_name]

    logger.warning(f"Dropping database: {db_name}")
    await client.drop_database(db_name)

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
        "created_at": None # Model will handle or we can set it
    }
    
    # We use 'users' collection directly
    await db.users.insert_one(admin_doc)
    
    # Re-create indexes via manual call or just let the app do it on next start
    await db.users.create_index("email", unique=True, sparse=True)
    await db.users.create_index("username", unique=True, sparse=True)
    await db.settings.create_index("key", unique=True)
    
    logger.info("✅ Database reset and Super-Admin seeded successfully.")
    client.close()

if __name__ == "__main__":
    asyncio.run(reset_db())
