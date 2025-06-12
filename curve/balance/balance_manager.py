"""
Curve Protocol balance manager.
Handles interactions with Curve pools and manages token balances.
"""

from typing import Dict, Optional, List, Tuple, Any
from decimal import Decimal
import json
from pathlib import Path
import sys
from web3 import Web3
import argparse
import time
from datetime import datetime
import os
from dotenv import load_dotenv

# Add parent directory to PYTHONPATH
sys.path.append(str(Path(__file__).parent.parent.parent))

from cowswap.cow_client import get_quote
from config.networks import NETWORK_TOKENS, RPC_URLS
from utils.retry import APIRetry
from curve.balance.reward_manager import CurveRewardManager

# Load environment variables
load_dotenv()

# Get production address from environment variable
DEFAULT_ADDRESS = os.getenv('PRODUCTION_ADDRESS', "0x66DbceE7feA3287B3356227d6F3DfF3CeFbC6F3C")

# Load markets configuration
MARKETS_PATH = Path(__file__).parent.parent / "markets" / "markets.json"
with open(MARKETS_PATH) as f:
    MARKETS_CONFIG = json.load(f)

def get_pool_address(network: str, pool_name: str) -> str:
    """Get pool address from markets.json"""
    return MARKETS_CONFIG["pool_address"]

def get_gauge_address(network: str, pool_name: str) -> str:
    """Get gauge address from markets.json"""
    return MARKETS_CONFIG["gauge"]

def get_lp_token_address(network: str, pool_name: str) -> str:
    """Get LP token address from markets.json"""
    return MARKETS_CONFIG["lp_token"]

def get_pool_abi(network: str, pool_name: str) -> str:
    """Get pool ABI name from markets.json"""
    return MARKETS_CONFIG["abi"]

class CurveBalanceManager:
    """
    Manages Curve Protocol interactions and balance tracking.
    """
    
    def __init__(self, network: str, w3: Web3):
        """
        Initialize the Curve balance manager.
        
        Args:
            network: Network identifier ('ethereum' or 'base')
            w3: Web3 instance for blockchain interaction
        """
        self.network = network
        self.w3 = w3
        self.network_tokens = NETWORK_TOKENS
        self.abis_path = Path(__file__).parent.parent / "abis"
        self.reward_manager = CurveRewardManager(network, w3)
        
    def get_gauge_balance(self, pool_name: str, user_address: str) -> Decimal:
        """
        Get the balance of LP tokens staked in a gauge.
        
        Args:
            pool_name: Name of the pool
            user_address: Address of the user
            
        Returns:
            Staked LP token balance
        """
        gauge_address = get_gauge_address(self.network, pool_name)
        
        # Load Child Liquidity Gauge ABI
        with open(self.abis_path / "Child Liquidity Gauge.json") as f:
            gauge_abi = json.load(f)
            
        gauge_contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(gauge_address),
            abi=gauge_abi
        )
        
        balance = gauge_contract.functions.balanceOf(
            self.w3.to_checksum_address(user_address)
        ).call()
        
        return Decimal(balance)

    def get_pool_data(self, pool_name: str, user_address: str) -> Dict:
        """
        Get all pool data including withdrawable amounts and their WETH values.
        
        Args:
            pool_name: Name of the pool
            user_address: Address of the user
            
        Returns:
            Dictionary containing all pool data
        """
        # Get LP token balance (already in wei)
        lp_balance = self.get_gauge_balance(pool_name, user_address)
        
        # Get pool contract
        pool_address = get_pool_address(self.network, pool_name)
        gauge_address = get_gauge_address(self.network, pool_name)
        abi_name = get_pool_abi(self.network, pool_name)
        
        with open(self.abis_path / f"{abi_name}.json") as f:
            pool_abi = json.load(f)
            
        pool_contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(pool_address),
            abi=pool_abi
        )
        
        # Initialize pool data structure
        pool_data = {
            "base": {
                pool_name: {
                    "staking_contract": gauge_address,
                    "amount": str(lp_balance),
                    "decimals": 18,
                    "tokens": {},
                    "rewards": {},
                    "totals": {
                        "wei": "0",
                        "formatted": "0"
                    }
                },
                "totals": {
                    "wei": "0",
                    "formatted": "0"
                }
            }
        }
        
        # Get token addresses and calculate withdrawable amounts
        weth_value = Decimal('0')
        best_method = ""
        
        for i in range(2):  # This pool has 2 tokens
            # Get token address
            token_address = pool_contract.functions.coins(i).call()
            
            # Calculate withdrawable amount - lp_balance is already in wei
            withdrawable = pool_contract.functions.calc_withdraw_one_coin(
                int(lp_balance),
                i
            ).call()
            
            # Get token symbol and decimals
            addr_lower = token_address.lower()
            symbol = "UNKNOWN"
            decimals = 18  # Default to 18 decimals
            
            # Search for token in NETWORK_TOKENS
            for token_name, token_data in NETWORK_TOKENS[self.network].items():
                if token_data["address"].lower() == addr_lower:
                    symbol = token_data["symbol"]
                    decimals = token_data["decimals"]
                    break
            
            # If this is WETH, just store the value
            if symbol == "WETH":
                weth_value = Decimal(withdrawable)
                best_method = "Direct WETH withdrawal"
            else:
                # Get CowSwap quote for non-WETH token
                try:
                    quote = get_quote(
                        sell_token=token_address,
                        buy_token=NETWORK_TOKENS[self.network]["WETH"]["address"],
                        amount=withdrawable,
                        network=self.network
                    )
                    
                    # Calculate WETH value from quote
                    token_in_weth = Decimal(quote["quote"]["quote"]["buyAmount"])
                    
                    # Add token data with WETH value
                    pool_data["base"][pool_name]["tokens"][symbol] = {
                        "amount": str(withdrawable),
                        "decimals": decimals,
                        "value": {
                            "WETH": {
                                "amount": str(token_in_weth),
                                "decimals": 18,
                                "conversion_details": {
                                    "source": "CoWSwap",
                                    "price_impact": quote["conversion_details"]["price_impact"],
                                    "rate": quote["conversion_details"]["rate"],
                                    "fee_percentage": quote["conversion_details"]["fee_percentage"],
                                    "fallback": quote["conversion_details"]["fallback"],
                                    "note": quote["conversion_details"]["note"]
                                }
                            }
                        },
                        "totals": {
                            "wei": str(token_in_weth),
                            "formatted": f"{token_in_weth / Decimal(10**18):.6f}"
                        }
                    }
                    
                    # Update best method if this gives more WETH
                    if token_in_weth > weth_value:
                        weth_value = token_in_weth
                        best_method = f"Withdraw {symbol} and swap to WETH"
                    
                except Exception as e:
                    print(f"Error getting CowSwap quote for {symbol}: {str(e)}")
        
        # Get rewards data
        rewards_data = self.reward_manager.get_claimable_rewards(pool_name, user_address)
        rewards_value = Decimal('0')
        if rewards_data and "curve" in rewards_data and "base" in rewards_data["curve"] and pool_name in rewards_data["curve"]["base"]:
            pool_data["base"][pool_name]["rewards"] = rewards_data["curve"]["base"][pool_name]["rewards"]
            # Add rewards value to total
            for reward_symbol, reward_data in pool_data["base"][pool_name]["rewards"].items():
                if "value" in reward_data and "WETH" in reward_data["value"]:
                    rewards_value += Decimal(reward_data["value"]["WETH"]["amount"])
        
        # Update totals with the best WETH value plus rewards
        total_value = weth_value + rewards_value
        pool_data["base"][pool_name]["totals"] = {
            "wei": str(int(total_value)),
            "formatted": f"{total_value / Decimal(10**18):.6f}",
            "note": f"Using {best_method} as it provides the highest WETH value, plus {rewards_value / Decimal(10**18):.6f} WETH in rewards"
        }
        
        # Update network totals
        pool_data["base"]["totals"] = {
            "wei": str(int(total_value)),
            "formatted": f"{total_value / Decimal(10**18):.6f}",
            "note": f"Using {best_method} as it provides the highest WETH value, plus {rewards_value / Decimal(10**18):.6f} WETH in rewards"
        }
        
        return pool_data

def main():
    """Main function to demonstrate usage."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Check Curve gauge balance')
    parser.add_argument('--address', type=str, default=DEFAULT_ADDRESS,
                      help=f'Address to check (default: {DEFAULT_ADDRESS})')
    args = parser.parse_args()
    
    # Initialize Web3
    w3 = Web3(Web3.HTTPProvider(RPC_URLS["base"]))
    
    if not w3.is_connected():
        print("Failed to connect to Base network")
        return
    
    # Initialize balance manager
    balance_manager = CurveBalanceManager("base", w3)
    
    try:
        # Get pool data
        print(f"\nFetching pool data for cbeth-f for address {args.address}...")
        pool_data = balance_manager.get_pool_data("cbeth-f", args.address)
        
        # Print withdrawable amounts
        print("\nWithdrawable amounts:")
        for symbol, data in pool_data["base"]["cbeth-f"]["tokens"].items():
            print(f"\n{symbol}:")
            print(f"  Amount: {Decimal(data['amount']) / Decimal(10**data['decimals']):.6f}")
            print(f"  Value in WETH: {Decimal(data['value']['WETH']['amount']) / Decimal(10**18):.6f}")
            print(f"  Conversion rate: {data['value']['WETH']['conversion_details']['rate']}")
            print(f"  Price impact: {data['value']['WETH']['conversion_details']['price_impact']}")
            print(f"  Fee: {data['value']['WETH']['conversion_details']['fee_percentage']}")
        
        # Print totals
        print("\nTotals:")
        print(f"Total value in WETH: {Decimal(pool_data['base']['cbeth-f']['totals']['wei']) / Decimal(10**18):.6f}")
        print(f"Note: {pool_data['base']['cbeth-f']['totals']['note']}")
        
        # Print full JSON structure
        print("\nFull data structure:")
        print(json.dumps(pool_data, indent=2))
            
    except Exception as e:
        print(f"\nError: {str(e)}")
        print("Make sure you're using a valid address with LP tokens staked in the pool.")

if __name__ == "__main__":
    main() 