import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import json
from web3 import Web3
from typing import Dict, Any
from decimal import Decimal

"""
Pendle balance manager module.
Handles balance fetching and USDC valuation for Pendle Principal Tokens (PT).
Integrates with Pendle's API for accurate price discovery and fallback mechanisms.
"""

# Add parent directory to PYTHONPATH
root_path = str(Path(__file__).parent.parent)
sys.path.append(root_path)

# Load environment variables from parent directory
load_dotenv(Path(root_path) / '.env')

from pendle.client import PendleClient
from config.networks import NETWORK_TOKENS
from .pt_to_usdc_converter import PendleSwapClient

class PendleBalanceManager:
    """
    Manages Pendle Principal Token (PT) positions and their USDC valuations.
    Provides balance aggregation across multiple networks (Ethereum, Base)
    with price discovery through Pendle's swap API.
    """
    
    def __init__(self):
        # Initialize Pendle clients for balance and swap operations
        self.client = PendleClient()
        self.swap_client = PendleSwapClient()
        
    def get_balances(self, address: str) -> Dict[str, Any]:
        """
        Retrieves and values all Pendle PT positions.
        """
        result = {"pendle": {}}
        
        # Process each supported network
        for network in ["ethereum", "base"]:
            network_tokens = NETWORK_TOKENS[network]
            network_result = {}
            
            # Find and process all Pendle PT tokens
            for token_symbol, token_data in network_tokens.items():
                if token_data.get("protocol") != "pendle":
                    continue
                    
                # Get token balance
                all_balances = self.client.get_balances(address)
                balance = int(all_balances[network][token_symbol]['amount']) if network in all_balances and token_symbol in all_balances[network] else 0
                
                if balance == 0:
                    continue
                
                balance_normalized = Decimal(balance) / Decimal(10**token_data["decimals"])
                
                # Get USDC valuation
                try:
                    usdc_amount, price_impact = self.swap_client.get_quote(
                        network=network,
                        token_symbol=token_symbol,
                        amount_in_wei=str(balance)
                    )
                    usdc_normalized = Decimal(usdc_amount) / Decimal(10**6)
                    
                    # Calculer le rate avant de l'afficher
                    rate = Decimal(usdc_amount) / Decimal(balance) * Decimal(10 ** (18 - 6)) if balance > 0 else Decimal('0')
                    
                    fallback = False
                    source = "Pendle API"
                except Exception as e:
                    usdc_amount = 0
                    price_impact = 0
                    rate = Decimal('0')  # Définir une valeur par défaut pour rate
                    fallback = True
                    source = "Failed"
                
                # Add position to results
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
            
            result["pendle"][network] = network_result
        
        return result

def main():
    """
    CLI utility for testing Pendle balance aggregation.
    Accepts address as argument or uses DEFAULT_USER_ADDRESS from environment.
    """
    test_address = sys.argv[1] if len(sys.argv) > 1 else os.getenv('DEFAULT_USER_ADDRESS')
    
    if not test_address:
        print("Error: No address provided and DEFAULT_USER_ADDRESS not found in .env")
        sys.exit(1)
        
    manager = PendleBalanceManager()
    balances = manager.get_balances(test_address)
    print(json.dumps(balances, indent=2))

if __name__ == "__main__":
    main()