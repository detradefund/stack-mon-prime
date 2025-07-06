import sys
from pathlib import Path
import json
from datetime import datetime, timezone
from dotenv import load_dotenv
from pymongo import MongoClient
from typing import Dict, Any
import logging
import os
from builder.aggregator import BalanceAggregator, build_overview

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

# Add parent directory to PYTHONPATH and load environment variables
root_path = str(Path(__file__).parent.parent)
env_path = Path(root_path) / '.env'
load_dotenv(env_path)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Debug: Check if .env file exists and variables are loaded
logger.info(f"Looking for .env file at: {env_path}")
logger.info(f".env file exists: {env_path.exists()}")
logger.info(f"MONGO_URI exists: {bool(os.getenv('MONGO_URI'))}")
logger.info(f"DATABASE_NAME exists: {bool(os.getenv('DATABASE_NAME'))}")
logger.info(f"COLLECTION_NAME exists: {bool(os.getenv('COLLECTION_NAME'))}")
logger.info(f"ADDRESSES exists: {bool(os.getenv('ADDRESSES'))}")

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
        
        # Initialize aggregator
        self.aggregator = BalanceAggregator()

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
            all_balances = self.aggregator.get_all_balances(address)
            if not all_balances:
                raise Exception("Failed to fetch portfolio data")
            logger.info("Portfolio data fetched successfully")

            # 2. Build overview
            logger.info("2. Building overview...")
            overview = build_overview(all_balances, address)
            logger.info("Overview built successfully")

            # 3. Prepare data for storage
            logger.info("3. Preparing data for storage...")
            push_timestamp = datetime.now(timezone.utc)
            
            # Combine overview with the rest of the data
            prepared_data = {
                'timestamp': collection_timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
                'created_at': push_timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
                'address': address,
                **overview,  # Add overview at the top
                'protocols': all_balances['protocols'],
                'spot': all_balances['spot']
            }
            
            # Convert large numbers to strings
            prepared_data = self.convert_large_numbers_to_strings(prepared_data)
            
            logger.info("Data prepared successfully")

            # 4. Store data in MongoDB
            logger.info("4. Storing data in MongoDB...")
            result = self.collection.insert_one(prepared_data)
            
            if not result.inserted_id:
                raise Exception("No document ID returned after insertion")
            
            logger.info(f"Document inserted with ID: {result.inserted_id}")

            # 5. Verify insertion
            logger.info("5. Verifying document insertion...")
            if self._verify_insertion(result.inserted_id):
                logger.info("Document verified in database")
            else:
                raise Exception("Document verification failed")

            # 6. Print summary with collection duration
            collection_duration = (push_timestamp - collection_timestamp).total_seconds()
            logger.info("="*80)
            logger.info("SUMMARY")
            logger.info("="*80)
            logger.info(f"Address: {address}")
            logger.info(f"Total Value: {overview['nav']['weth']} WETH")
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
    # Configuration for multiple addresses and databases
    configurations = [
        {
            'address': '0x66DbceE7feA3287B3356227d6F3DfF3CeFbC6F3C',
            'database_name': 'detrade-core-eth',
            'collection_name': 'oracle'
        }
    ]
    
    for config in configurations:
        pusher = BalancePusher(
            database_name=config['database_name'],
            collection_name=config['collection_name']
        )
        try:
            pusher.push_balance_data(config['address'])
        finally:
            pusher.close()

if __name__ == "__main__":
    main()