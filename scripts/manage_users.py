import os
import sys
import bcrypt
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime, timezone

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def add_admin(username, password, name):
    load_dotenv()
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/xoai")
    
    # Simple fallback check for host resolution
    if "xoai-mongo" in mongo_uri:
        # Check if we are outside docker
        import socket
        try:
            socket.gethostbyname("xoai-mongo")
        except socket.gaierror:
            mongo_uri = mongo_uri.replace("xoai-mongo", "localhost")

    client = MongoClient(mongo_uri)
    db_name = mongo_uri.split("/")[-1].split("?")[0] or "xoai"
    db = client[db_name]
    
    user_doc = {
        "username": username,
        "name": name,
        "password_hash": hash_password(password),
        "role": "admin",
        "status": "approved",
        "email": None,
        "email_verified": True,
        "lang": "EN",
        "created_at": datetime.now(timezone.utc)
    }
    
    try:
        # Check if exists
        if db.users.find_one({"username": username}):
            print(f"⚠️  User '{username}' already exists. Updating role to admin...")
            db.users.update_one({"username": username}, {"$set": {"role": "admin", "status": "approved"}})
        else:
            db.users.insert_one(user_doc)
            print(f"✅ Admin user '{username}' created successfully.")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python3 manage_users.py add admin <username> <password> <name>")
        sys.exit(1)
        
    cmd = sys.argv[1]
    role = sys.argv[2]
    
    if cmd == "add" and role == "admin":
        add_admin(sys.argv[3], sys.argv[4], sys.argv[5])
