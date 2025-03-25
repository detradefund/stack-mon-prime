import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import json
from web3 import Web3
from typing import Dict, Any
from decimal import Decimal

# Add parent directory to PYTHONPATH
root_path = str(Path(__file__).parent.parent)
sys.path.append(root_path)

# Load environment variables from parent directory
load_dotenv(Path(root_path) / '.env')

from pendle.client import PendleClient
from config.networks import NETWORK_TOKENS
from .pt_to_usdc_converter import PendleSwapClient

class PendleBalanceManager:
    """Manages Pendle PT token balances and their conversions"""
    
    def __init__(self):
        self.client = PendleClient()
        self.swap_client = PendleSwapClient()
        
    def get_balances(self, address: str) -> Dict[str, Any]:
        """
        Get all Pendle PT balances and their USDC values for an address
        """
        result = {"pendle": {}}
        
        # Iterate through networks
        for network in ["ethereum", "base"]:
            network_tokens = NETWORK_TOKENS[network]
            network_result = {}
            
            # Get PT token balances for this network
            for token_symbol, token_data in network_tokens.items():
                if token_data.get("protocol") != "pendle":
                    continue
                    
                # Get PT token balance
                all_balances = self.client.get_balances(address)
                balance = int(all_balances[network][token_symbol]['amount']) if network in all_balances and token_symbol in all_balances[network] else 0
                
                if balance == 0:
                    continue
                
                # Get USDC conversion
                try:
                    usdc_amount, price_impact = self.swap_client.get_quote(
                        network=network,
                        token_symbol=token_symbol,
                        amount_in_wei=str(balance)
                    )
                    fallback = False
                    source = "Pendle API"
                except Exception as e:
                    print(f"Warning: Pendle API failed: {str(e)}")
                    usdc_amount = 0
                    price_impact = 0
                    fallback = True
                    source = "Failed"
                
                # Calculate rate
                if balance > 0:
                    rate = Decimal(usdc_amount) / Decimal(balance) * Decimal(10 ** (18 - 6))
                else:
                    rate = Decimal('0')
                
                # Build response structure
                network_result[token_symbol] = {
                    "amount": str(balance),
                    "decimals": token_data["decimals"],
                    "value": {
                        "USDC": {
                            "amount": str(usdc_amount),
                            "decimals": 6,
                            "conversion_details": {
                                "source": source,
                                "price_impact": f"{price_impact:.6f}",
                                "rate": f"{rate:.6f}",
                                "fallback": fallback
                            }
                        }
                    }
                }
            
            if network_result:
                result["pendle"][network] = network_result
                
        return result

def main():
    # Use provided address or default address from .env
    test_address = sys.argv[1] if len(sys.argv) > 1 else os.getenv('DEFAULT_USER_ADDRESS')
    
    if not test_address:
        print("Error: No address provided and DEFAULT_USER_ADDRESS not found in .env")
        sys.exit(1)
        
    manager = PendleBalanceManager()
    balances = manager.get_balances(test_address)
    print(json.dumps(balances, indent=2))

if __name__ == "__main__":
    main()