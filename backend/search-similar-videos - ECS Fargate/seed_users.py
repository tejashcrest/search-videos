#!/usr/bin/env python3
"""
Seed DocumentDB with initial admin users.
Runs once at container startup to ensure users exist.
"""
import os
import sys
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from passlib.hash import bcrypt

def seed_users():
    """Seed DocumentDB with two admin users if they don't exist."""
    
    # Get DocumentDB connection details from environment
    docdb_uri = os.environ.get("DOCDB_URI", "").strip()
    docdb_db = os.environ.get("DOCDB_DB", "video_search").strip()
    docdb_collection = os.environ.get("DOCDB_USERS_COLLECTION", "users").strip()
    
    # Skip if no DocumentDB URI (dev mode)
    if not docdb_uri:
        print("ℹ️  No DOCDB_URI found - skipping user seeding (dev mode)")
        return True
    
    # Define default admin users with shorter passwords (bcrypt has 72 byte limit)
    default_users = [
        {
            "username": "admin1",
            "email": "admin1@example.com",
            "password": "Admin123!Change"  # Shorter password
        },
        {
            "username": "admin2", 
            "email": "admin2@example.com",
            "password": "Admin456!Change"  # Shorter password
        }
    ]
    
    try:
        print(f"🔗 Connecting to DocumentDB: {docdb_db}.{docdb_collection}")
        
        # Connect to DocumentDB with TLS certificate if available
        tls_ca_file = "/app/global-bundle.pem" if os.path.exists("/app/global-bundle.pem") else None
        
        client = MongoClient(
            docdb_uri,
            serverSelectionTimeoutMS=10000,
            connectTimeoutMS=10000,
            socketTimeoutMS=10000,
            tlsCAFile=tls_ca_file
        )
        
        # Test connection
        client.admin.command('ping')
        print("✅ Connected to DocumentDB")
        
        # Get database and collection
        db = client[docdb_db]
        users = db[docdb_collection]
        
        # Seed each user
        seeded_count = 0
        for user_data in default_users:
            username = user_data["username"]
            
            # Check if user already exists
            existing = users.find_one({"username": username})
            if existing:
                print(f"ℹ️  User '{username}' already exists - skipping")
                continue
            
            # Truncate password to 72 bytes for bcrypt (bcrypt limitation)
            password = user_data["password"][:72]
            
            # Hash password and insert user
            try:
                password_hash = bcrypt.hash(password)
            except Exception as e:
                print(f"⚠️  Error hashing password for {username}: {e}")
                # Fallback: use bcrypt directly
                import bcrypt as bcrypt_lib
                password_hash = bcrypt_lib.hashpw(password.encode('utf-8'), bcrypt_lib.gensalt()).decode('utf-8')
            
            user_doc = {
                "username": username,
                "email": user_data["email"],
                "password_hash": password_hash
            }
            
            users.insert_one(user_doc)
            seeded_count += 1
            print(f"✅ Created user: {username}")
        
        if seeded_count > 0:
            print(f"\n🎉 Successfully seeded {seeded_count} user(s)")
            print("\n📋 Login credentials:")
            for user_data in default_users:
                print(f"   Username: {user_data['username']}, Password: {user_data['password']}")
        else:
            print("\n✅ All users already exist - no seeding needed")
        
        client.close()
        return True
        
    except PyMongoError as e:
        print(f"❌ DocumentDB error: {e}", file=sys.stderr)
        print("⚠️  Continuing without seeding - users may need to be created manually", file=sys.stderr)
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        print("⚠️  Continuing without seeding - users may need to be created manually", file=sys.stderr)
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🌱 DocumentDB User Seeding")
    print("=" * 60)
    
    success = seed_users()
    
    print("=" * 60)
    
    # Don't fail container startup if seeding fails
    # Users can be created manually later
    sys.exit(0)
