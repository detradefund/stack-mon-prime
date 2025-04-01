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
        print("\n=== Processing Sky Protocol positions ===")
        print(f"Checking sUSDS balances for {address}")
        
        balances = self.sky_client.get_balances(address)
        
        # Log position details if any were found
        if "sky" in balances:
            for network, network_data in balances["sky"].items():
                if network_data:
                    print(f"\n{network.upper()} Network:")
                    for token, data in network_data.items():
                        amount = Decimal(data['amount']) / Decimal(10**data['decimals'])
                        usds_amount = Decimal(data['value']['USDS']['amount']) / Decimal(10**data['value']['USDS']['decimals'])
                        usdc_value = Decimal(data['value']['USDC']['amount']) / Decimal(10**6)
                        conversion = data['value']['USDC']['conversion_details']
                        print(f"- {token}:")
                        print(f"  Amount: {amount:.6f}")
                        print(f"  USDS Value: {usds_amount:.6f}")
                        print(f"  USDC Value: {usdc_value:.6f}")
                        print(f"  Rate: {conversion['rate']}")
                        print(f"  Source: {conversion['source']}")
                        print(f"  Price Impact: {conversion['price_impact']}")
        else:
            print("No Sky Protocol positions found")
        
        print("=== Sky Protocol processing complete ===\n")
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