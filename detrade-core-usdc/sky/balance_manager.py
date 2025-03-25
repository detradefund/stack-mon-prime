import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import json

# Add parent directory to PYTHONPATH
root_path = str(Path(__file__).parent.parent)
sys.path.append(root_path)

from datetime import datetime
from decimal import Decimal
from sky.client import SkyClient

# Load environment variables
load_dotenv()

class BalanceManager:
    def __init__(self):
        self.sky_client = SkyClient()

    def get_balances(self, address: str = "0x0000000000000000000000000000000000000000") -> dict:
        return {
            "sky": self.sky_client.get_balances(address)
        }

if __name__ == "__main__":
    # Use provided address or default address from .env
    test_address = sys.argv[1] if len(sys.argv) > 1 else os.getenv('DEFAULT_USER_ADDRESS')
    
    if not test_address:
        print("Error: No address provided and DEFAULT_USER_ADDRESS not found in .env")
        sys.exit(1)
        
    manager = BalanceManager()
    balances = manager.get_balances(test_address)
    
    # Pretty print avec une indentation de 2 espaces
    print(json.dumps(balances, indent=2)) 