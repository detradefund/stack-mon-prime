from pymongo import MongoClient
import os
from dotenv import load_dotenv
from bson.objectid import ObjectId
import sys

# Load environment variables
load_dotenv()

def delete_document(doc_id: str) -> None:
    """Delete a document from MongoDB by its _id"""
    try:
        # Get MongoDB configuration
        mongo_uri = os.getenv('MONGO_URI')
        database_name = os.getenv('DATABASE_NAME_1')
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
        
        # Convert string ID to ObjectId
        object_id = ObjectId(doc_id)
        
        # Find document before deletion
        doc = collection.find_one({"_id": object_id})
        if not doc:
            print(f"\n❌ Document with ID {doc_id} not found")
            return
            
        # Print document details before deletion
        print("\nDocument to delete:")
        print("="*80)
        print(f"ID: {doc_id}")
        print(f"Address: {doc.get('address', 'N/A')}")
        print(f"Created at: {doc.get('created_at', 'N/A')}")
        if 'nav' in doc:
            print(f"Total Value: {doc['nav']['usdc']} USDC")
        print("="*80)
        
        # Confirm deletion
        confirm = input("\nAre you sure you want to delete this document? (y/N): ")
        if confirm.lower() != 'y':
            print("Deletion cancelled")
            return
            
        # Delete document
        result = collection.delete_one({"_id": object_id})
        
        if result.deleted_count == 1:
            print("\n✓ Document successfully deleted")
        else:
            print("\n❌ Failed to delete document")
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
    finally:
        client.close()
        print("\n✓ MongoDB connection closed")

def main():
    """CLI entry point for document deletion"""
    if len(sys.argv) != 2:
        print("Usage: python -m scripts.delete_document <document_id>")
        print("Example: python -m scripts.delete_document 6808a235759fa6a5b09dcc63")
        sys.exit(1)
        
    doc_id = sys.argv[1]
    delete_document(doc_id)

if __name__ == "__main__":
    main() 