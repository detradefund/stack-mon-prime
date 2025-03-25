import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from pymongo import MongoClient
from balance_aggregator import BalanceAggregator
from apscheduler.schedulers.blocking import BlockingScheduler

# Add parent directory to PYTHONPATH and load environment variables
root_path = str(Path(__file__).parent.parent)
load_dotenv(Path(root_path) / '.env')

class BalancePusher:
    def __init__(self):
        # MongoDB connection setup
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
        try:
            # Get balance data
            print("\n========================================")
            print(f"Fetching balance data for {address}")
            print("========================================\n")
            
            balance_data = self.aggregator.get_total_usdc_value(address)
            
            # Add metadata
            balance_data['address'] = address
            balance_data['created_at'] = datetime.utcnow()
            
            # Insert into MongoDB
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
        self.client.close()

def main():
    # Get address from command line or .env
    test_address = os.getenv('DEFAULT_USER_ADDRESS')
    
    if not test_address:
        print("Error: DEFAULT_USER_ADDRESS not found in .env")
        exit(1)
    
    pusher = BalancePusher()
    try:
        # Créer le scheduler
        scheduler = BlockingScheduler()
        
        # Ajouter la tâche à exécuter toutes les 10 minutes
        scheduler.add_job(
            pusher.push_balance_data,
            'interval',
            minutes=10,
            args=[test_address]
        )
        
        print("Starting scheduler. Press Ctrl+C to exit.")
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("Stopping scheduler...")
    finally:
        pusher.close()

if __name__ == "__main__":
    main() 