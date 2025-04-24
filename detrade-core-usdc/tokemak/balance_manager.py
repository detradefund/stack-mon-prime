import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from web3 import Web3
from typing import Dict, Any
from dotenv import load_dotenv
from config.networks import NETWORK_TOKENS, RPC_URLS
from decimal import Decimal
from cowswap.cow_client import get_quote

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
        
        # Setup Web3 with RPC_URLS instead of NETWORK_TOKENS
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
        print("\n" + "="*80)
        print("TOKEMAK BALANCE MANAGER")
        print("="*80)
        
        print("\nProcessing network: ethereum")
        
        checksum_address = Web3.to_checksum_address(address)
        result = {
            "tokemak": {
                "usdc_totals": {
                    "total": {
                        "wei": 0,
                        "formatted": "0.000000"
                    }
                }
            }
        }
        
        try:
            # Contract information
            print("\nContract information:")
            print(f"  main_rewarder: {self.MAIN_REWARDER_ADDRESS} (MainRewarder)")
            print(f"  token: {self.AUTO_USD_ADDRESS} (autoUSD)")
            
            # Get shares balance
            print("\nQuerying staked autoUSD balance:")
            print(f"  Contract: {self.MAIN_REWARDER_ADDRESS}")
            print("  Function: balanceOf(address) - Returns user's staked autoUSD balance")
            shares = self.main_rewarder.functions.balanceOf(checksum_address).call()
            
            if shares == 0:
                print("No staked balance found")
                return result
                
            print(f"  Amount: {shares} (decimals: 18)")
            print(f"  Formatted: {(Decimal(shares) / Decimal(10**18)):.6f} autoUSD")

            # Convert shares to USDC value
            print("\nConverting autoUSD to USDC:")
            print(f"  Contract: {self.AUTO_USD_ADDRESS}")
            print("  Function: convertToAssets(uint256) - Returns equivalent USDC amount")
            assets = self.auto_pool.functions.convertToAssets(shares).call()
            
            # Calculate real conversion rate
            rate = Decimal(assets) / Decimal(shares) * Decimal(10**12) if shares > 0 else Decimal('0')
            
            print(f"  USDC value: {(Decimal(assets) / Decimal(10**6)):.6f} USDC")
            print(f"  Rate: {rate:.6f} USDC/autoUSD")
            print("  Price impact: 0.0000%")
            
            # Get rewards
            print("\nQuerying reward token (TOKE):")
            print(f"  Contract: {self.MAIN_REWARDER_ADDRESS}")
            print("  Function: earned(address) - Returns pending TOKE rewards")
            earned = self.main_rewarder.functions.earned(checksum_address).call()
            print(f"  Amount: {earned} (decimals: 18)")
            print(f"  Formatted: {(Decimal(earned) / Decimal(10**18)):.6f} TOKE")
            
            # Convert TOKE to USDC via CoWSwap
            print("\nConverting TOKE to USDC via CoWSwap:")
            
            quote_result = get_quote(
                network="ethereum",
                sell_token=NETWORK_TOKENS['ethereum']['TOKE']['address'],
                buy_token=NETWORK_TOKENS['ethereum']['USDC']['address'],
                amount=str(earned),
                token_decimals=18,
                token_symbol='TOKE'
            )
            
            if quote_result["quote"]:
                toke_in_usdc = int(quote_result["quote"]["quote"]["buyAmount"])
                conversion_details = quote_result["conversion_details"]
                
                # Handle case where price_impact is "N/A"
                if conversion_details.get("price_impact") == "N/A":
                    conversion_details["price_impact"] = "0.0000%"
                
                print(f"✓ Converted to USDC: {toke_in_usdc/1e6:.6f} USDC")
                print(f"  Rate: {conversion_details['rate']} USDC/TOKE")
                print(f"  Source: {conversion_details['source']}")
                print(f"  Note: {conversion_details['note']}")
                
                total_usdc_value = assets + toke_in_usdc

            # Calculate totals
            print("\nCalculating USDC totals:")
            print(f"  LP tokens: {assets/1e6:.6f} USDC")
            print(f"  Rewards: {toke_in_usdc/1e6:.6f} USDC")
            print(f"  Total: {total_usdc_value/1e6:.6f} USDC")

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
                },
                "rewards": {
                    "TOKE": {
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
                },
                "usdc_totals": {
                    "lp_tokens_total": {
                        "wei": assets,
                        "formatted": f"{assets/1e6:.6f}"
                    },
                    "rewards_total": {
                        "wei": toke_in_usdc,
                        "formatted": f"{toke_in_usdc/1e6:.6f}"
                    },
                    "total": {
                        "wei": total_usdc_value,
                        "formatted": f"{total_usdc_value/1e6:.6f}"
                    }
                }
            }

            result["tokemak"]["usdc_totals"] = {
                "total": {
                    "wei": total_usdc_value,
                    "formatted": f"{total_usdc_value/1e6:.6f}"
                }
            }

            print("\n[Tokemak] Calculation complete")
            
            # Print position summary
            print(f"tokemak.ethereum.autoUSD: {assets/1e6:.6f} USDC")
            print(f"tokemak.ethereum.rewards.TOKE: {toke_in_usdc/1e6:.6f} USDC")

        except Exception as e:
            print(f"\nError processing Tokemak balances: {str(e)}")
            return result

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
    
    print("\n" + "="*80)
    print("FINAL RESULT:")
    print("="*80 + "\n")
    print(json.dumps(balances, indent=2))

if __name__ == "__main__":
    main() 