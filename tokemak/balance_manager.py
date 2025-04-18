import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import json
from web3 import Web3
from typing import Dict, Any
from decimal import Decimal

"""
Tokemak balance manager module.
Handles balance fetching and USDC valuation for Tokemak positions.
"""

# Add the current directory to PYTHONPATH
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Load environment variables
load_dotenv(os.path.join(current_dir, '.env'))

from config.networks import NETWORK_TOKENS
from cowswap.cow_client import get_quote

class TokemakBalanceManager:
    def __init__(self):
        # Contract addresses
        self.MAIN_REWARDER_ADDRESS = "0x726104CfBd7ece2d1f5b3654a19109A9e2b6c27B"
        self.AUTO_USD_ADDRESS = NETWORK_TOKENS['ethereum']['autoUSD']['address']
        
        # Setup Web3
        self.w3 = Web3(Web3.HTTPProvider(os.getenv('ETHEREUM_RPC')))
        
        # Load ABIs
        self.CURRENT_DIR = Path(__file__).parent
        self.load_abis()

    def load_abis(self):
        """Load contract ABIs"""
        self.auto_pool_abi = self.load_abi('AutopoolETH.json')
        self.main_rewarder_abi = self.load_abi('AutopoolMainRewarder.json')

    def load_abi(self, filename):
        """Load a single ABI file"""
        abi_path = self.CURRENT_DIR / 'abis' / filename
        with open(abi_path) as f:
            return json.load(f)

    def get_shares(self, address):
        """Get shares balance for address"""
        contract = self.w3.eth.contract(
            address=self.MAIN_REWARDER_ADDRESS, 
            abi=self.main_rewarder_abi
        )
        try:
            return contract.functions.balanceOf(address).call()
        except Exception as e:
            print(f"Error getting shares balance: {e}")
            return None

    def get_usdc_value(self, shares):
        """Convert shares to USDC value"""
        contract = self.w3.eth.contract(
            address=self.AUTO_USD_ADDRESS, 
            abi=self.auto_pool_abi
        )
        try:
            return contract.functions.convertToAssets(shares).call()
        except Exception as e:
            print(f"Error converting shares to USDC: {e}")
            return None

    def get_earned_toke(self, address):
        """Get earned TOKE rewards"""
        contract = self.w3.eth.contract(
            address=self.MAIN_REWARDER_ADDRESS, 
            abi=self.main_rewarder_abi
        )
        try:
            return contract.functions.earned(address).call()
        except Exception as e:
            print(f"Error getting earned TOKE: {e}")
            return None

    def get_toke_value_in_usdc(self, toke_amount):
        """Get TOKE value in USDC"""
        try:
            quote = get_quote(
                network="ethereum",
                sell_token=NETWORK_TOKENS["ethereum"]["TOKE"]["address"],
                buy_token=NETWORK_TOKENS["ethereum"]["USDC"]["address"],
                amount=str(toke_amount)
            )
            
            if isinstance(quote, dict) and 'quote' in quote:
                return int(quote['quote']['buyAmount']), False
            else:
                print("Warning: Direct quote failed, using estimation")
                return self.estimate_toke_value_in_usdc(toke_amount), True
        except Exception as e:
            print(f"Warning: Quote failed ({e}), using estimation")
            return self.estimate_toke_value_in_usdc(toke_amount), True

    def estimate_toke_value_in_usdc(self, toke_amount):
        """Estimate TOKE value using reference amount"""
        try:
            reference_amount = 1000 * 10**18
            quote = get_quote(
                network="ethereum",
                sell_token=NETWORK_TOKENS["ethereum"]["TOKE"]["address"],
                buy_token=NETWORK_TOKENS["ethereum"]["USDC"]["address"],
                amount=str(reference_amount)
            )
            
            if isinstance(quote, dict) and 'quote' in quote:
                reference_usdc = int(quote['quote']['buyAmount'])
                price_per_toke = reference_usdc / reference_amount
                estimated_value = int(price_per_toke * toke_amount)
                print(f"Estimated price: {price_per_toke * 10**18:.6f} USDC/TOKE")
                return estimated_value
            else:
                print(f"Error getting reference quote: {quote}")
                return None
        except Exception as e:
            print(f"Error in estimation: {e}")
            return None

    def get_balances(self, address: str) -> dict:
        """
        Gets all Tokemak balances and formats them for the aggregator
        """
        # Initialize result structure
        result = {
            "tokemak": {
                "ethereum": {}  # Tokemak is only on Ethereum
            }
        }

        # Get autoUSD shares and value
        shares = self.get_shares(address)
        if shares:
            usdc_value = self.get_usdc_value(shares)
            earned_toke = self.get_earned_toke(address)
            
            total_usdc_value = 0
            
            # Add autoUSD details
            if usdc_value is not None:
                total_usdc_value += usdc_value
                result["tokemak"]["ethereum"]["autoUSD"] = {
                    "amount": str(shares),
                    "decimals": 18,
                    "value": {
                        "USDC": {
                            "amount": str(usdc_value),
                            "decimals": 6,
                            "conversion_details": {
                                "source": "Tokemak",
                                "price_impact": "0.0000%",
                                "rate": "1.000000",
                                "fee_percentage": "0.0000%",
                                "fallback": False
                            }
                        }
                    }
                }

            # Add TOKE details
            if earned_toke:
                toke_value_result = self.get_toke_value_in_usdc(earned_toke)
                if toke_value_result is not None:
                    toke_in_usdc, is_fallback = toke_value_result
                    total_usdc_value += toke_in_usdc
                    result["tokemak"]["ethereum"]["TOKE"] = {
                        "amount": str(earned_toke),
                        "decimals": 18,
                        "value": {
                            "USDC": {
                                "amount": str(toke_in_usdc),
                                "decimals": 6,
                                "conversion_details": {
                                    "source": "CoWSwap-Fallback" if is_fallback else "CoWSwap",
                                    "price_impact": "N/A",
                                    "rate": str(toke_in_usdc / float(earned_toke) * 10**12),
                                    "fee_percentage": "N/A",
                                    "fallback": is_fallback,
                                    "fallback_reference": "1000 units" if is_fallback else None
                                }
                            }
                        }
                    }

            # Add total value for positions_in_usdc aggregation
            if total_usdc_value > 0:
                result["total_value"] = str(total_usdc_value)

        return result

def main():
    """
    CLI utility for testing Tokemak balance aggregation.
    Accepts address as argument or uses DEFAULT_USER_ADDRESS from environment.
    """
    test_address = sys.argv[1] if len(sys.argv) > 1 else os.getenv('DEFAULT_USER_ADDRESS')
    
    if not test_address:
        print("Error: No address provided and DEFAULT_USER_ADDRESS not found in .env")
        sys.exit(1)
        
    manager = TokemakBalanceManager()
    balances = manager.get_balances(test_address)
    print(json.dumps(balances, indent=2))

if __name__ == "__main__":
    main() 