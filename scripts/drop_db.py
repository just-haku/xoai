import os
from pymongo import MongoClient
from dotenv import load_dotenv

def drop_db():
    load_dotenv()
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/xoai")
    
    # Check if we should try a localhost fallback for Docker service names
    uris_to_try = [mongo_uri]
    if "xoai-mongo" in mongo_uri:
        uris_to_try.append(mongo_uri.replace("xoai-mongo", "localhost"))

    for uri in uris_to_try:
        print(f"⚠️  Trying to connect to: {uri}")
        try:
            # Set a 5-second timeout for server selection
            client = MongoClient(uri, serverSelectionTimeoutMS=5000)
            db_name = uri.split("/")[-1].split("?")[0] or "xoai"
            
            # Use 'ping' to verify connection
            client.admin.command('ping')
            
            print(f"⚠️  Dropping database: {db_name}")
            client.drop_database(db_name)
            print("✅ Database dropped successfully.")
            return
        except Exception as e:
            print(f"ℹ️  Connection to {uri} failed: {e}")

    print("❌ Could not connect to MongoDB on any attempted URI.")

if __name__ == "__main__":
    drop_db()
