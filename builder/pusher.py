import os
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
from pymongo import MongoClient
from typing import Dict, Any
import logging
from builder.aggregator import main as aggregator_main

# Add parent directory to PYTHONPATH and load environment variables
root_path = str(Path(__file__).parent.parent)
load_dotenv(Path(root_path) / '.env')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class BalancePusher:
    """
    Handles the storage of portfolio balances in MongoDB.
    Acts as a bridge between the BalanceAggregator and the database.
    """
    def __init__(self, database_name=None, collection_name=None):
        # Required MongoDB configuration from environment variables
        self.mongo_uri = os.getenv('MONGO_URI')
        self.database_name = database_name or os.getenv('DATABASE_NAME')
        self.collection_name = collection_name or os.getenv('COLLECTION_NAME')
        
        if not all([self.mongo_uri, self.database_name, self.collection_name]):
            raise ValueError("Missing required environment variables for MongoDB connection")
        
        # Initialize MongoDB connection
        self._init_mongo_connection()

    def _init_mongo_connection(self) -> None:
        """Initialize MongoDB connection and verify access"""
        try:
            self.client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=5000)
            self.db = self.client[self.database_name]
            self.collection = self.db[self.collection_name]
            
            # Test connection with timeout
            self.client.admin.command('ping')
            logger.info("MongoDB connection initialized successfully")
            logger.info(f"Database: {self.database_name}")
            logger.info(f"Collection: {self.collection_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize MongoDB connection: {str(e)}")
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
            logger.error(f"Failed to verify document insertion: {str(e)}")
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
            
            logger.info("="*80)
            logger.info(f"PUSHING BALANCE DATA FOR {address}")
            logger.info("="*80)

            # 1. Fetch current portfolio data
            logger.info("1. Fetching portfolio data...")
            logger.info(f"Collection started at: {collection_timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            balance_data = aggregator_main(address)
            if not balance_data:
                raise Exception("Failed to fetch portfolio data")
            logger.info("Portfolio data fetched successfully")

            # 2. Prepare data for storage
            logger.info("2. Preparing data for storage...")
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
            
            logger.info("Data prepared successfully")

            # 3. Store data in MongoDB
            logger.info("3. Storing data in MongoDB...")
            result = self.collection.insert_one(prepared_data)
            
            if not result.inserted_id:
                raise Exception("No document ID returned after insertion")
            
            logger.info(f"Document inserted with ID: {result.inserted_id}")

            # 4. Verify insertion
            logger.info("4. Verifying document insertion...")
            if self._verify_insertion(result.inserted_id):
                logger.info("Document verified in database")
            else:
                raise Exception("Document verification failed")

            # 5. Print summary avec la durée de collection
            collection_duration = (push_timestamp - collection_timestamp).total_seconds()
            logger.info("="*80)
            logger.info("SUMMARY")
            logger.info("="*80)
            logger.info(f"Address: {address}")
            logger.info(f"Total Value: {balance_data['nav']['usdc']} USDC")
            logger.info(f"Collection started at: {prepared_data['timestamp']}")
            logger.info(f"Pushed at: {push_timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            logger.info(f"Collection duration: {collection_duration:.2f} seconds")
            logger.info(f"Database: {self.database_name}")
            logger.info(f"Collection: {self.collection_name}")
            logger.info(f"Document ID: {result.inserted_id}")
            logger.info("="*80)

        except Exception as e:
            logger.error(f"Error in push_balance_data: {str(e)}")
            raise
        
    def close(self):
        """Close MongoDB connection"""
        try:
            self.client.close()
            logger.info("MongoDB connection closed")
        except Exception as e:
            logger.error(f"Error closing MongoDB connection: {str(e)}")

def main():
    """CLI entry point for testing balance pushing functionality."""
    # Get addresses from environment variables
    addresses = os.getenv('ADDRESSES', '').split(',')
    if not addresses:
        logger.error("No addresses configured in environment variables")
        return

    # Get database configuration from environment variables
    database_name = os.getenv('DATABASE_NAME')
    collection_name = os.getenv('COLLECTION_NAME')
    
    if not all([database_name, collection_name]):
        logger.error("Missing database configuration in environment variables")
        return
    
    for address in addresses:
        address = address.strip()
        if not address:
            continue
            
        pusher = BalancePusher(
            database_name=database_name,
            collection_name=collection_name
        )
        try:
            pusher.push_balance_data(address)
        finally:
            pusher.close()

if __name__ == "__main__":
    main()