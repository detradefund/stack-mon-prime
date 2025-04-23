import sys
from pathlib import Path
# Ajouter le répertoire parent au PYTHONPATH
sys.path.append(str(Path(__file__).parent.parent))

from web3 import Web3
from decimal import Decimal
from typing import Dict, Any
from dotenv import load_dotenv
from config.networks import RPC_URLS, NETWORK_TOKENS

"""
Sky Protocol balance manager module.
Provides high-level interface for fetching Sky Protocol positions and balances.
Handles direct interaction with Sky Protocol contracts and balance aggregation.
"""

# Load environment variables
load_dotenv()

# Minimal ABI for sUSDS contract
MINIMAL_SUSDS_ABI = [
    {
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "shares", "type": "uint256"}],
        "name": "convertToAssets",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

class BalanceManager:
    def __init__(self):
        # Initialize Web3 connections
        self.eth_w3 = Web3(Web3.HTTPProvider(RPC_URLS['ethereum']))
        self.base_w3 = Web3(Web3.HTTPProvider(RPC_URLS['base']))
        
        # Initialize contracts
        self.eth_contract = self.eth_w3.eth.contract(
            address=NETWORK_TOKENS['ethereum']['sUSDS']['address'],
            abi=MINIMAL_SUSDS_ABI
        )
        self.base_contract = self.base_w3.eth.contract(
            address=NETWORK_TOKENS['base']['sUSDS']['address'],
            abi=MINIMAL_SUSDS_ABI
        )

    def get_balances(self, address: str) -> Dict[str, Any]:
        """Get Sky Protocol balances for the given address"""
        checksum_address = Web3.to_checksum_address(address)
        result = {"sky": {}}
        total_usdc_wei = 0

        # Process each network
        for network, contract in [("ethereum", self.eth_contract), ("base", self.base_contract)]:
            try:
                # Get balance
                balance = contract.functions.balanceOf(checksum_address).call()
                
                if balance > 0:
                    # Convert to USDS
                    usds_value = self.eth_contract.functions.convertToAssets(balance).call()
                    
                    # Assuming 1:1 conversion rate between USDS and USDC
                    usdc_amount = (usds_value * 10**6) // 10**18
                    
                    result["sky"][network] = {
                        "sUSDS": {
                            "amount": str(balance),
                            "decimals": 18,
                            "value": {
                                "USDC": {
                                    "amount": str(usdc_amount),
                                    "decimals": 6,
                                    "conversion_details": {
                                        "source": "Sky Protocol",
                                        "price_impact": "0.0000%",
                                        "rate": "1.000000",
                                        "fee_percentage": "0.0000%",
                                        "fallback": False,
                                        "note": "Direct conversion using sUSDS contract"
                                    }
                                }
                            }
                        },
                        "usdc_totals": {
                            "total": {
                                "wei": usdc_amount,
                                "formatted": f"{usdc_amount/1e6:.6f}"
                            }
                        }
                    }
                    total_usdc_wei += usdc_amount

            except Exception as e:
                print(f"Error processing {network}: {str(e)}")
                continue

        # Add protocol total
        if total_usdc_wei > 0:
            result["sky"]["usdc_totals"] = {
                "total": {
                    "wei": total_usdc_wei,
                    "formatted": f"{total_usdc_wei/1e6:.6f}"
                }
            }

        return result

def main():
    """CLI utility for testing"""
    import os
    import json
    
    test_address = sys.argv[1] if len(sys.argv) > 1 else os.getenv('DEFAULT_USER_ADDRESS')
    if not test_address:
        print("Error: No address provided and DEFAULT_USER_ADDRESS not found in .env")
        sys.exit(1)
        
    manager = BalanceManager()
    balances = manager.get_balances(test_address)
    print(json.dumps(balances, indent=2))

if __name__ == "__main__":
    main() 