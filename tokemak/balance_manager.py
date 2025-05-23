import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from web3 import Web3
from typing import Dict, Any
from dotenv import load_dotenv
from config.networks import NETWORK_TOKENS, RPC_URLS
from decimal import Decimal
from cowswap.cow_client import get_quote
from utils.retry import Web3Retry, APIRetry

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
        self.w3 = Web3(Web3.HTTPProvider(RPC_URLS['ethereum']))
        self.base_w3 = Web3(Web3.HTTPProvider(RPC_URLS['base']))
        
        # Initialize contracts for each network
        self.contracts = {
            'ethereum': {
                'autoETH': self.w3.eth.contract(
                    address=NETWORK_TOKENS['ethereum']['autoETH']['address'],
                    abi=MINIMAL_ABI
                ),
                'autoETH_rewarder': self.w3.eth.contract(
                    address=NETWORK_TOKENS['ethereum']['autoETH']['rewarder'],
                    abi=MINIMAL_ABI
                ),
                'TOKE': self.w3.eth.contract(
                    address=NETWORK_TOKENS['ethereum']['TOKE']['address'],
                    abi=MINIMAL_ABI
                )
            },
            'base': {
                'baseETH': self.base_w3.eth.contract(
                    address=NETWORK_TOKENS['base']['baseETH']['address'],
                    abi=MINIMAL_ABI
                ),
                'baseETH_rewarder': self.base_w3.eth.contract(
                    address=NETWORK_TOKENS['base']['baseETH']['rewarder'],
                    abi=MINIMAL_ABI
                )
            }
        }

    def get_token_balance(self, network: str, token: str, address: str) -> Dict[str, Any]:
        """Get balance for a specific token, checking both spot and staked positions"""
        print(f"\nProcessing {token} on {network}:")
        
        checksum_address = Web3.to_checksum_address(address)
        result = {
            "amount": "0",
            "decimals": 18,
            "value": {
                "WETH": {
                    "amount": "0",
                    "decimals": 18,
                    "conversion_details": {
                        "source": "Tokemak",
                        "price_impact": "0.0000%",
                        "rate": "0",
                        "fee_percentage": "0.0000%",
                        "fallback": False,
                        "note": "No balance"
                    }
                }
            },
            "rewards": {
                "TOKE": {
                    "amount": "0",
                    "decimals": 18,
                    "value": {
                        "USDC": {
                            "amount": "0",
                            "decimals": 6,
                            "conversion_details": {
                                "source": "Direct",
                                "price_impact": "0.0000%",
                                "rate": "0",
                                "fee_percentage": "0.0000%",
                                "fallback": False,
                                "note": "No rewards"
                            }
                        }
                    }
                }
            },
            "totals": {
                "wei": 0,
                "formatted": "0.000000"
            }
        }

        try:
            # Get spot balance
            print(f"Checking spot balance for {token}:")
            spot_balance = Web3Retry.call_contract_function(
                self.contracts[network][token].functions.balanceOf(checksum_address).call
            )
            print(f"  Spot balance: {spot_balance} wei")

            # Get staked balance
            print(f"Checking staked balance for {token}:")
            staked_balance = Web3Retry.call_contract_function(
                self.contracts[network][f"{token}_rewarder"].functions.balanceOf(checksum_address).call
            )
            print(f"  Staked balance: {staked_balance} wei")

            total_balance = spot_balance + staked_balance
            if total_balance == 0:
                print("No balance found (spot or staked)")
                return result

            # Convert total balance to assets
            print(f"\nConverting {token} to WETH:")
            assets = Web3Retry.call_contract_function(
                self.contracts[network][token].functions.convertToAssets(total_balance).call
            )
            
            # Calculate conversion rate
            rate = Decimal(assets) / Decimal(total_balance) if total_balance > 0 else Decimal('0')
            
            print(f"  WETH value: {(Decimal(assets) / Decimal(10**18)):.6f} WETH")
            print(f"  Rate: {rate:.6f} WETH/{token}")
            print("  Price impact: 0.0000%")

            # Get rewards if staked
            if staked_balance > 0:
                print(f"\nQuerying TOKE rewards for staked {token}:")
                earned = Web3Retry.call_contract_function(
                    self.contracts[network][f"{token}_rewarder"].functions.earned(checksum_address).call
                )
                print(f"  Amount: {earned} wei")
                print(f"  Formatted: {(Decimal(earned) / Decimal(10**18)):.6f} TOKE")

                # Convert TOKE to USDC via CoWSwap
                if earned > 0:
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
                        
                        if conversion_details.get("price_impact") == "N/A":
                            conversion_details["price_impact"] = "0.0000%"
                        
                        print(f"✓ Converted to USDC: {toke_in_usdc/1e6:.6f} USDC")
                        print(f"  Rate: {conversion_details['rate']} USDC/TOKE")
                        print(f"  Source: {conversion_details['source']}")
                        print(f"  Note: {conversion_details['note']}")

                        # Update rewards in result
                        result["rewards"]["TOKE"] = {
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

            # Update main result
            result["amount"] = str(total_balance)
            result["value"]["WETH"] = {
                "amount": str(assets),
                "decimals": 18,
                "conversion_details": {
                    "source": "Tokemak",
                    "price_impact": "0.0000%",
                    "rate": str(rate),
                    "fee_percentage": "0.0000%",
                    "fallback": False,
                    "note": "Direct conversion using Tokemak contract"
                }
            }
            result["totals"] = {
                "wei": assets,
                "formatted": f"{Decimal(assets) / Decimal(10**18):.6f}"
            }

        except Exception as e:
            print(f"\nError processing {token} balance: {str(e)}")
            return result

        return result

    def get_balances(self, address: str) -> Dict[str, Any]:
        """Get all Tokemak balances and rewards for address"""
        print("\n" + "="*80)
        print("TOKEMAK BALANCE MANAGER")
        print("="*80)
        
        result = {
            "tokemak": {
                "ethereum": {
                    "autoETH": self.get_token_balance("ethereum", "autoETH", address),
                    "totals": {
                        "wei": 0,
                        "formatted": "0.000000"
                    }
                },
                "base": {
                    "baseETH": self.get_token_balance("base", "baseETH", address),
                    "totals": {
                        "wei": 0,
                        "formatted": "0.000000"
                    }
                },
                "totals": {
                    "wei": 0,
                    "formatted": "0.000000"
                }
            }
        }

        # Calculate totals
        eth_total = int(result["tokemak"]["ethereum"]["autoETH"]["totals"]["wei"])
        base_total = int(result["tokemak"]["base"]["baseETH"]["totals"]["wei"])
        
        result["tokemak"]["ethereum"]["totals"] = {
            "wei": eth_total,
            "formatted": f"{Decimal(eth_total) / Decimal(10**18):.6f}"
        }
        
        result["tokemak"]["base"]["totals"] = {
            "wei": base_total,
            "formatted": f"{Decimal(base_total) / Decimal(10**18):.6f}"
        }
        
        result["tokemak"]["totals"] = {
            "wei": eth_total + base_total,
            "formatted": f"{Decimal(eth_total + base_total) / Decimal(10**18):.6f}"
        }

        return result

def main():
    """CLI utility for testing"""
    import json
    
    # Use command line argument if provided, otherwise use production address
    test_address = sys.argv[1] if len(sys.argv) > 1 else "0x66DbceE7feA3287B3356227d6F3DfF3CeFbC6F3C"
    
    manager = BalanceManager()
    balances = manager.get_balances(test_address)
    
    print("\n" + "="*80)
    print("FINAL RESULT:")
    print("="*80 + "\n")
    print(json.dumps(balances, indent=2))

if __name__ == "__main__":
    main() 