import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import json
from typing import Dict, Any

"""
Sky Protocol balance manager module.
Provides high-level interface for fetching Sky Protocol positions and balances.
Used by balance aggregator for portfolio valuation.
"""

# Add parent directory to PYTHONPATH
root_path = str(Path(__file__).parent.parent)
sys.path.append(root_path)

from datetime import datetime
from decimal import Decimal
from sky.client import SkyClient

# Load environment variables
load_dotenv()

class BalanceManager:
    """
    Manages balance fetching for Sky Protocol positions.
    Wraps SkyClient to provide standardized balance reporting format.
    """
    
    def __init__(self):
        # Initialize Sky Protocol client
        self.sky_client = SkyClient()

    def get_balances(self, address: str = "0x0000000000000000000000000000000000000000") -> dict:
        """
        Retrieves all Sky Protocol positions for a given address.
        """
        balances = self.sky_client.get_balances(address)
        
        return {
            "sky": balances
        }

def main():
    """
    CLI utility for testing Sky Protocol balance fetching.
    Accepts address as argument or uses DEFAULT_USER_ADDRESS from environment.
    """
    # Use provided address or default address from .env
    test_address = sys.argv[1] if len(sys.argv) > 1 else os.getenv('DEFAULT_USER_ADDRESS')
    
    if not test_address:
        print("Error: No address provided and DEFAULT_USER_ADDRESS not found in .env")
        sys.exit(1)
        
    manager = BalanceManager()
    balances = manager.get_balances(test_address)
    
    # Pretty print results with 2-space indentation
    print(json.dumps(balances, indent=2)) 