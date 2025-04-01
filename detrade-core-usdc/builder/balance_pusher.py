import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from pymongo import MongoClient
from balance_aggregator import BalanceAggregator

# Add parent directory to PYTHONPATH and load environment variables
root_path = str(Path(__file__).parent.parent)
load_dotenv(Path(root_path) / '.env')

class BalancePusher:
    """
    Handles the storage of portfolio balances in MongoDB.
    Acts as a bridge between the BalanceAggregator and the database.
    """
    def __init__(self):
        # Required MongoDB configuration from environment variables
        mongo_uri = os.getenv('MONGO_URI')
        database_name = os.getenv('DATABASE_NAME_1')
        collection_name = os.getenv('COLLECTION_NAME')
        
        if not all([mongo_uri, database_name, collection_name]):
            raise ValueError("Missing required environment variables for MongoDB connection")
        
        self.client = MongoClient(mongo_uri)
        self.db = self.client[database_name]
        self.collection = self.db[collection_name]
        self.aggregator = BalanceAggregator()

    def push_balance_data(self, address: str) -> None:
        """
        Fetches current portfolio balance and stores it in MongoDB.
        Creates a timestamped snapshot of all positions and their values.
        """
        try:
            print("\n========================================")
            print(f"Fetching balance data for {address}")
            print("========================================\n")
            
            # Get current portfolio snapshot from aggregator
            balance_data = self.aggregator.get_total_usdc_value(address)
            
            # Add metadata for historical tracking
            balance_data['address'] = address
            balance_data['created_at'] = datetime.utcnow()
            
            # Store snapshot in database
            print("\n=== Pushing data to MongoDB ===")
            result = self.collection.insert_one(balance_data)
            print(f"Document successfully pushed with _id: {result.inserted_id}")
            print("\n========================================")
            print(f"Total Value: {balance_data['nav']['usdc']} USDC")
            print(f"Timestamp: {balance_data['timestamp']}")
            print("========================================\n")
            
        except Exception as e:
            print(f"\n❌ Error pushing data to MongoDB: {str(e)}")
            raise
        
    def close(self):
        """Closes MongoDB connection"""
        self.client.close()

def main():
    """
    CLI entry point for testing balance pushing functionality.
    Uses DEFAULT_USER_ADDRESS from .env file.
    """
    test_address = os.getenv('DEFAULT_USER_ADDRESS')
    
    if not test_address:
        print("Error: DEFAULT_USER_ADDRESS not found in .env")
        exit(1)
    
    pusher = BalancePusher()
    try:
        pusher.push_balance_data(test_address)
    finally:
        pusher.close()

if __name__ == "__main__":
    main() 