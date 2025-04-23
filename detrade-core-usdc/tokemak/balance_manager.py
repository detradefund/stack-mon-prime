import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from web3 import Web3
from typing import Dict, Any
from dotenv import load_dotenv
from config.networks import NETWORK_TOKENS, RPC_URLS

"""
Tokemak balance manager module.
Handles balance fetching and USDC valuation for Tokemak positions.
"""

# Load environment variables
load_dotenv()

# Minimal ABI for Tokemak contracts
MINIMAL_ABI = [
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
    },
    {
        "inputs": [{"name": "account", "type": "address"}],
        "name": "earned",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

class BalanceManager:
    def __init__(self):
        # Contract addresses
        self.MAIN_REWARDER_ADDRESS = "0x726104CfBd7ece2d1f5b3654a19109A9e2b6c27B"
        self.AUTO_USD_ADDRESS = NETWORK_TOKENS['ethereum']['autoUSD']['address']
        
        # Setup Web3 avec RPC_URLS au lieu de NETWORK_TOKENS
        self.w3 = Web3(Web3.HTTPProvider(RPC_URLS['ethereum']))
        
        # Initialize contracts
        self.auto_pool = self.w3.eth.contract(
            address=self.AUTO_USD_ADDRESS,
            abi=MINIMAL_ABI
        )
        self.main_rewarder = self.w3.eth.contract(
            address=self.MAIN_REWARDER_ADDRESS,
            abi=MINIMAL_ABI
        )

    def get_balances(self, address: str) -> Dict[str, Any]:
        """Get Tokemak balances and rewards for address"""
        checksum_address = Web3.to_checksum_address(address)
        result = {"tokemak": {}}
        
        try:
            # Get shares balance
            shares = self.main_rewarder.functions.balanceOf(checksum_address).call()
            if shares == 0:
                return result

            # Get USDC value and rewards
            assets = self.auto_pool.functions.convertToAssets(shares).call()
            earned = self.main_rewarder.functions.earned(checksum_address).call()
            
            # Assuming 1:1 conversion for TOKE rewards to keep it simple
            toke_in_usdc = (earned * 10**6) // 10**18
            total_usdc_value = assets + toke_in_usdc

            result["tokemak"]["ethereum"] = {
                "autoUSD": {
                    "amount": str(shares),
                    "decimals": 18,
                    "value": {
                        "USDC": {
                            "amount": str(assets),
                            "decimals": 6,
                            "conversion_details": {
                                "source": "Tokemak",
                                "price_impact": "0.0000%",
                                "rate": "1.000000",
                                "fee_percentage": "0.0000%",
                                "fallback": False,
                                "note": "Direct conversion using autoUSD contract"
                            }
                        }
                    }
                }
            }

            if earned > 0:
                result["tokemak"]["ethereum"]["TOKE"] = {
                    "amount": str(earned),
                    "decimals": 18,
                    "value": {
                        "USDC": {
                            "amount": str(toke_in_usdc),
                            "decimals": 6,
                            "conversion_details": {
                                "source": "Simple conversion",
                                "price_impact": "0.0000%",
                                "rate": "1.000000",
                                "fee_percentage": "0.0000%",
                                "fallback": True,
                                "note": "Simplified 1:1 conversion"
                            }
                        }
                    }
                }

            # Add totals
            result["tokemak"]["ethereum"]["usdc_totals"] = {
                "total": {
                    "wei": total_usdc_value,
                    "formatted": f"{total_usdc_value/1e6:.6f}"
                }
            }

            result["tokemak"]["usdc_totals"] = {
                "total": {
                    "wei": total_usdc_value,
                    "formatted": f"{total_usdc_value/1e6:.6f}"
                }
            }

        except Exception as e:
            print(f"Error processing Tokemak balances: {str(e)}")

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