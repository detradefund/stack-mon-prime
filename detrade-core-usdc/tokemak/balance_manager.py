import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import json
from web3 import Web3
from typing import Dict, Any
from decimal import Decimal
import time

"""
Tokemak balance manager module.
Handles balance fetching and USDC valuation for Tokemak positions.
"""

# Add parent directory to PYTHONPATH
root_path = str(Path(__file__).parent.parent)
sys.path.append(root_path)

# Load environment variables from parent directory
load_dotenv(Path(root_path) / '.env')

from config.networks import NETWORK_TOKENS
from cowswap.cow_client import get_quote

class BalanceManager:
    """
    Tokemak balance manager module.
    Handles balance fetching and USDC valuation for Tokemak positions.
    """
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
        """Get TOKE value in USDC using reference amount for consistent pricing"""
        retry_delays = [1, 3, 3]  # Delays in seconds between attempts
        
        print("\nAttempting to get quote for TOKE:")
        
        for attempt, delay in enumerate(retry_delays, 1):
            try:
                print(f"[Attempt {attempt}/3] Requesting CoWSwap quote...")
                
                # Try direct quote first
                quote = get_quote(
                    network="ethereum",
                    sell_token=NETWORK_TOKENS["ethereum"]["TOKE"]["address"],
                    buy_token=NETWORK_TOKENS["ethereum"]["USDC"]["address"],
                    amount=str(toke_amount)
                )
                
                if isinstance(quote, dict) and 'quote' in quote:
                    # Calculate rate correctly (USDC per token)
                    sell_amount = Decimal(quote['quote']['sellAmount']) / Decimal(10**18)
                    buy_amount = Decimal(quote['quote']['buyAmount']) / Decimal(10**6)
                    rate = buy_amount / sell_amount if sell_amount else Decimal('0')
                    
                    print(f"✓ Direct quote successful:")
                    print(f"  - Sell amount: {sell_amount} TOKE")
                    print(f"  - Buy amount: {buy_amount} USDC")
                    print(f"  - Rate: {float(rate):.6f} USDC/TOKE")
                    print(f"  - Fee: {float(quote['quote'].get('feeAmount', 0))/float(quote['quote'].get('sellAmount', 1))*100:.4f}%")
                    
                    return int(quote['quote']['buyAmount']), {
                        "source": "CoWSwap",
                        "price_impact": f"{float(quote['quote'].get('priceImpact', 0))*100:.4f}%",
                        "rate": f"{float(rate):.6f}",
                        "fee_percentage": f"{float(quote['quote'].get('feeAmount', 0))/float(quote['quote'].get('sellAmount', 1))*100:.4f}%",
                        "fallback": False,
                        "note": "Direct CoWSwap quote"
                    }

                # Handle small amounts
                if "SellAmountDoesNotCoverFee" in str(quote):
                    print("! Amount too small for direct quote, trying fallback method...")
                    reference_amount = 1000 * 10**18  # 1000 TOKE
                    
                    print(f"Requesting quote with reference amount (1000 TOKE)...")
                    fallback_quote = get_quote(
                        network="ethereum",
                        sell_token=NETWORK_TOKENS["ethereum"]["TOKE"]["address"],
                        buy_token=NETWORK_TOKENS["ethereum"]["USDC"]["address"],
                        amount=str(reference_amount)
                    )
                    
                    if isinstance(fallback_quote, dict) and 'quote' in fallback_quote:
                        # Calculate rate using normalized amounts
                        sell_amount = Decimal(fallback_quote['quote']['sellAmount']) / Decimal(10**18)
                        buy_amount = Decimal(fallback_quote['quote']['buyAmount']) / Decimal(10**6)
                        rate = buy_amount / sell_amount if sell_amount else Decimal('0')
                        
                        # Apply rate to original amount
                        original_amount_normalized = Decimal(toke_amount) / Decimal(10**18)
                        estimated_value = int(original_amount_normalized * rate * Decimal(10**6))
                        
                        print(f"✓ Fallback successful:")
                        print(f"  - Discovered rate: {float(rate):.6f} USDC/TOKE")
                        print(f"  - Estimated value: {estimated_value/10**6:.6f} USDC")
                        
                        return estimated_value, {
                            "source": "CoWSwap-Fallback",
                            "price_impact": "0.0000%",
                            "rate": f"{float(rate):.6f}",
                            "fee_percentage": "N/A",
                            "fallback": True,
                            "note": "Using reference amount of 1000 tokens for price discovery due to small amount"
                        }
                    
                    print("✗ Fallback method failed")
                
                print(f"✗ CoWSwap error: {str(quote)[:200]}...")
                
                if attempt < len(retry_delays):
                    print(f"  Retrying in {delay} seconds...")
                    time.sleep(delay)
                    continue
                
            except Exception as e:
                print(f"✗ Technical error (attempt {attempt}/3):")
                print(f"  {str(e)}")
                
                if attempt < len(retry_delays):
                    print(f"  Retrying in {delay} seconds...")
                    time.sleep(delay)
                    continue
        
        print("✗ All retry attempts failed")
        return None

    def get_balances(self, address: str) -> Dict[str, Any]:
        """Get Tokemak balances and rewards for address"""
        
        print("\n" + "="*80)
        print("TOKEMAK BALANCE MANAGER")
        print("="*80 + "\n")
        
        print("Debug get_balances:")
        print(f"Processing address: {address}")
        checksum_address = Web3.to_checksum_address(address)
        print(f"Checksum address: {checksum_address}")

        # Get shares balance
        try:
            shares = self.get_shares(checksum_address)
            if shares == 0:
                print("ℹ No Tokemak positions found")
                return {}
            
            # Continue with reward and asset conversion only if shares > 0
            earned = self.get_earned_toke(checksum_address)
            assets = self.get_usdc_value(shares)
            
            if assets is None:
                print("Error: Unable to get USDC value from shares")
                return {}
            
            total_usdc_value = assets
            
            result = {
                "tokemak": {
                    "ethereum": {}  # Tokemak is only on Ethereum
                }
            }

            # Add autoUSD details
            if assets is not None:
                total_usdc_value = assets
                print(f"USDC Value: {assets/1e6:.6f} USDC")
                result["tokemak"]["ethereum"]["autoUSD"] = {
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
                                "note": "Direct conversion using autoUSD.convertToAssets() function from Tokemak autoUSD contract"
                            }
                        }
                    }
                }

            # Add TOKE details
            if earned:
                print("\nProcessing TOKE rewards:")
                print(f"Amount: {earned} (decimals: 18)")
                print(f"Formatted amount: {earned/1e18:.6f} TOKE\n")
                
                toke_value_result = self.get_toke_value_in_usdc(earned)
                if toke_value_result is not None:
                    toke_in_usdc, conversion_details = toke_value_result
                    total_usdc_value += toke_in_usdc
                    
                    result["tokemak"]["ethereum"]["TOKE"] = {
                        "amount": str(earned),
                        "decimals": 18,
                        "value": {
                            "USDC": {
                                "amount": str(toke_in_usdc),
                                "decimals": 6,
                                "conversion_details": conversion_details
                            }
                        }
                    }

            # Add usdc_totals for ethereum chain
            result["tokemak"]["ethereum"]["usdc_totals"] = {
                "lp_tokens_total": {
                    "wei": int(assets),
                    "formatted": f"{assets/1e6:.6f}"
                },
                "rewards_total": {
                    "wei": int(toke_in_usdc) if earned and toke_value_result else 0,
                    "formatted": f"{(toke_in_usdc if earned and toke_value_result else 0)/1e6:.6f}"
                },
                "total": {
                    "wei": int(total_usdc_value),
                    "formatted": f"{total_usdc_value/1e6:.6f}"
                }
            }

            # Add total value for positions_in_usdc aggregation
            if total_usdc_value > 0:
                print("\n" + "="*80)
                print(f"TOTAL TOKEMAK VALUE: {total_usdc_value/1e6:.6f} USDC")
                print("="*80)
                result["total_value"] = str(total_usdc_value)

            return result

        except Exception as e:
            print(f"Error getting shares balance: {str(e)}")
            return {}

def format_tokemak_data(balances):
    """
    Formats Tokemak balance data to match the desired structure
    """
    formatted_data = {
        "tokemak": {
            "ethereum": {
                "autoUSD": {
                    "amount": balances["tokemak"]["ethereum"]["autoUSD"]["amount"],
                    "decimals": 18,
                    "value": {
                        "USDC": balances["tokemak"]["ethereum"]["autoUSD"]["value"]["USDC"]
                    }
                },
                "rewards": {
                    "TOKE": {
                        "amount": balances["tokemak"]["ethereum"]["TOKE"]["amount"],
                        "decimals": 18,
                        "value": {
                            "USDC": balances["tokemak"]["ethereum"]["TOKE"]["value"]["USDC"]
                        }
                    }
                },
                "usdc_totals": {
                    "lp_tokens_total": {
                        "wei": int(balances["tokemak"]["ethereum"]["autoUSD"]["value"]["USDC"]["amount"]),
                        "formatted": f"{int(balances['tokemak']['ethereum']['autoUSD']['value']['USDC']['amount'])/1e6:.6f}"
                    },
                    "rewards_total": {
                        "wei": int(balances["tokemak"]["ethereum"]["TOKE"]["value"]["USDC"]["amount"]),
                        "formatted": f"{int(balances['tokemak']['ethereum']['TOKE']['value']['USDC']['amount'])/1e6:.6f}"
                    },
                    "total": {
                        "wei": int(balances["tokemak"]["ethereum"]["autoUSD"]["value"]["USDC"]["amount"]) + 
                              int(balances["tokemak"]["ethereum"]["TOKE"]["value"]["USDC"]["amount"]),
                        "formatted": f"{(int(balances['tokemak']['ethereum']['autoUSD']['value']['USDC']['amount']) + int(balances['tokemak']['ethereum']['TOKE']['value']['USDC']['amount']))/1e6:.6f}"
                    }
                }
            }
        }
    }
    return formatted_data

def main():
    """
    CLI utility for testing Tokemak balance aggregation.
    Accepts address as argument or uses DEFAULT_USER_ADDRESS from environment.
    """
    test_address = sys.argv[1] if len(sys.argv) > 1 else os.getenv('DEFAULT_USER_ADDRESS')
    
    if not test_address:
        print("Error: No address provided and DEFAULT_USER_ADDRESS not found in .env")
        sys.exit(1)
        
    manager = BalanceManager()
    balances = manager.get_balances(test_address)
    formatted_balances = format_tokemak_data(balances)
    print(json.dumps(formatted_balances, indent=2))

if __name__ == "__main__":
    main() 