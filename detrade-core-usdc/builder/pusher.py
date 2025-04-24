import os
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
from pymongo import MongoClient
from typing import Dict, Any
from builder.aggregator import main as aggregator_main

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
        self.mongo_uri = os.getenv('MONGO_URI')
        self.database_name = os.getenv('DATABASE_NAME')
        self.collection_name = os.getenv('COLLECTION_NAME')
        
        if not all([self.mongo_uri, self.database_name, self.collection_name]):
            raise ValueError("Missing required environment variables for MongoDB connection")
        
        # Initialize MongoDB connection
        self._init_mongo_connection()

    def _init_mongo_connection(self) -> None:
        """Initialize MongoDB connection and verify access"""
        try:
            self.client = MongoClient(self.mongo_uri)
            self.db = self.client[self.database_name]
            self.collection = self.db[self.collection_name]
            
            # Test connection
            self.client.admin.command('ping')
            print("\n✓ MongoDB connection initialized successfully")
            print(f"Database: {self.database_name}")
            print(f"Collection: {self.collection_name}\n")
            
        except Exception as e:
            print(f"\n❌ Failed to initialize MongoDB connection: {str(e)}")
            raise

    def _prepare_balance_data(self, raw_data: Dict[str, Any], address: str) -> Dict[str, Any]:
        """Prepare balance data for storage"""
        # Convert large numbers to strings
        data = self.convert_large_numbers_to_strings(raw_data)
        
        # Add metadata
        timestamp = datetime.now(timezone.utc)
        data.update({
            'address': address,
            'created_at': timestamp,
            'timestamp': timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
        })
        
        return data

    def _verify_insertion(self, doc_id: Any) -> bool:
        """Verify document was properly inserted"""
        try:
            inserted_doc = self.collection.find_one({"_id": doc_id})
            return bool(inserted_doc)
        except Exception as e:
            print(f"❌ Failed to verify document insertion: {str(e)}")
            return False

    def convert_large_numbers_to_strings(self, data: Dict) -> Dict:
        """Recursively converts large integers to strings"""
        if isinstance(data, dict):
            return {k: self.convert_large_numbers_to_strings(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.convert_large_numbers_to_strings(x) for x in data]
        elif isinstance(data, int) and data > 2**53:
            return str(data)
        return data

    def push_balance_data(self, address: str) -> None:
        """
        Main method to fetch and store portfolio balance data.
        """
        try:
            # Capture start time in UTC for data collection
            collection_timestamp = datetime.now(timezone.utc)
            
            print("\n" + "="*80)
            print(f"PUSHING BALANCE DATA FOR {address}")
            print("="*80 + "\n")

            # 1. Fetch current portfolio data
            print("1. Fetching portfolio data...")
            print(f"Collection started at: {collection_timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            balance_data = aggregator_main()
            print("✓ Portfolio data fetched successfully\n")

            # 2. Prepare data for storage
            print("2. Preparing data for storage...")
            push_timestamp = datetime.now(timezone.utc)
            
            # Add both timestamps to the data
            prepared_data = self.convert_large_numbers_to_strings(balance_data)
            
            # Reorganize fields with timestamp first
            prepared_data = {
                'timestamp': collection_timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
                'created_at': push_timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
                'address': address,
                **prepared_data  # Rest of the data
            }
            
            print("✓ Data prepared successfully\n")

            # 3. Store data in MongoDB
            print("3. Storing data in MongoDB...")
            result = self.collection.insert_one(prepared_data)
            
            if not result.inserted_id:
                raise Exception("No document ID returned after insertion")
            
            print(f"✓ Document inserted with ID: {result.inserted_id}\n")

            # 4. Verify insertion
            print("4. Verifying document insertion...")
            if self._verify_insertion(result.inserted_id):
                print("✓ Document verified in database\n")
            else:
                raise Exception("Document verification failed")

            # 5. Print summary avec la durée de collection
            collection_duration = (push_timestamp - collection_timestamp).total_seconds()
            print("="*80)
            print("SUMMARY")
            print("="*80)
            print(f"Address: {address}")
            print(f"Total Value: {balance_data['nav']['usdc']} USDC")
            print(f"Collection started at: {prepared_data['timestamp']}")
            print(f"Pushed at: {push_timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            print(f"Collection duration: {collection_duration:.2f} seconds")
            print(f"Database: {self.database_name}")
            print(f"Collection: {self.collection_name}")
            print(f"Document ID: {result.inserted_id}")
            print("="*80 + "\n")

        except Exception as e:
            print(f"\n❌ Error in push_balance_data: {str(e)}")
            raise
        
    def close(self):
        """Close MongoDB connection"""
        try:
            self.client.close()
            print("✓ MongoDB connection closed")
        except Exception as e:
            print(f"❌ Error closing MongoDB connection: {str(e)}")

def main():
    """CLI entry point for testing balance pushing functionality."""
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