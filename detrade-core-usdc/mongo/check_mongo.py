from pymongo import MongoClient
import os
from dotenv import load_dotenv
from datetime import datetime
from pprint import pprint

# Load environment variables
load_dotenv()

def check_mongodb():
    """Check MongoDB connection and display recent documents"""
    try:
        # Get MongoDB configuration
        mongo_uri = os.getenv('MONGO_URI')
        database_name = os.getenv('DATABASE_NAME')
        collection_name = os.getenv('COLLECTION_NAME')
        
        print("\nConnecting to MongoDB...")
        print(f"Database: {database_name}")
        print(f"Collection: {collection_name}\n")
        
        # Connect to MongoDB
        client = MongoClient(mongo_uri)
        
        # Test connection
        client.admin.command('ping')
        print("✓ Connection successful!")
        
        # Get database and collection
        db = client[database_name]
        collection = db[collection_name]
        
        # Get most recent document
        print("\nFetching most recent document...")
        doc = collection.find_one(
            sort=[('created_at', -1)]
        )
        
        if doc:
            print("\nMost recent document:")
            print("="*80)
            print(f"ID: {doc['_id']}")
            print(f"Address: {doc['address']}")
            print(f"Created at: {doc['created_at']}")
            print(f"Total Value: {doc['nav']['usdc']} USDC")
            print("="*80)
        else:
            print("No documents found in collection")
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
    finally:
        client.close()

if __name__ == "__main__":
    check_mongodb() 