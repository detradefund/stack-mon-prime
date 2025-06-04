"""
Master script to manage Curve positions, balances, and conversions.
"""
from typing import Dict, List, Optional, Any
from web3 import Web3
from decimal import Decimal
import json
import os
from dotenv import load_dotenv
from datetime import datetime
from pathlib import Path
import sys

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from curve.markets.pools import CurvePool
from curve.balance.balance_manager import CurveBalanceManager, MARKETS_CONFIG
from curve.balance.reward_manager import CurveRewardManager
from config.networks import RPC_URLS

# Load environment variables
load_dotenv()

class CurveManager:
    def __init__(self, wallet_address: str):
        """
        Initialize the CurveManager.
        
        Args:
            wallet_address: The wallet address to manage positions for
        """
        self.wallet_address = wallet_address
        self.positions = {}
        self.rewards_balances = {}
        self.network = "base"  # Default to base network
        self.w3 = Web3(Web3.HTTPProvider(RPC_URLS[self.network]))
        self.balance_manager = CurveBalanceManager(self.network, self.w3)
        self.reward_manager = CurveRewardManager(self.network, self.w3)
        
    def check_balances(self):
        """Check all pool balances and rewards."""
        print("\n=== Checking Balances ===")
        self.positions = {}
        
        # Check pool balances
        print("\nChecking pool balances...")
        # Get pool name from MARKETS_CONFIG
        pool_name = MARKETS_CONFIG.get("name", "cbeth-f")
        
        try:
            pool_balances = self.balance_manager.get_pool_balances(pool_name)
            user_balances = self.balance_manager.get_user_balances(pool_name, self.wallet_address)
            
            if any(balance > 0 for _, _, balance in user_balances):
                self.positions[pool_name] = {
                    "staking_contract": MARKETS_CONFIG.get("pool_address", ""),
                    "amount": "0",
                    "decimals": 18,
                    "value": {
                        "WETH": {
                            "amount": "0",
                            "decimals": 18,
                            "conversion_details": {
                                "source": "Direct",
                                "price_impact": "0",
                                "rate": "1.000000",
                                "fee_percentage": "0.0000%",
                                "fallback": False,
                                "note": "Direct 1:1 conversion"
                            }
                        },
                        "cbETH": {
                            "amount": "0",
                            "decimals": 18,
                            "conversion_details": {
                                "source": "CoWSwap",
                                "price_impact": "0",
                                "rate": "0.000000",
                                "fee_percentage": "0.0000%",
                                "fallback": False,
                                "note": "Direct CoWSwap quote"
                            }
                        }
                    },
                    "rewards": {},
                    "totals": {
                        "wei": "0",
                        "formatted": "0.000000"
                    }
                }
                
                # Process balances
                total_wei = 0
                for addr, symbol, balance in user_balances:
                    if balance > 0:
                        balance_wei = int(balance * Decimal(10**18))
                        if symbol == "WETH":
                            self.positions[pool_name]["value"]["WETH"]["amount"] = str(balance_wei)
                            total_wei += balance_wei
                        elif symbol == "cbETH":
                            quote_result = self.reward_manager._get_quote_with_fallback(
                                addr,
                                balance_wei,
                                18,
                                symbol
                            )
                            if quote_result:
                                self.positions[pool_name]["value"]["cbETH"].update({
                                    "amount": str(balance_wei),
                                    "conversion_details": quote_result["conversion_details"]
                                })
                                total_wei += int(quote_result["amount"])
                
                self.positions[pool_name]["amount"] = str(total_wei)
            
        except Exception as e:
            print(f"Error checking balances for pool {pool_name}: {str(e)}")
        
        # Check rewards
        print("\nChecking rewards...")
        for pool_name in self.positions.keys():
            try:
                rewards_data = self.reward_manager.get_claimable_rewards(pool_name, self.wallet_address)
                if rewards_data["curve"]["base"][pool_name]["rewards"]:
                    rewards = rewards_data["curve"]["base"][pool_name]["rewards"]
                    for symbol in rewards:
                        if "totals" in rewards[symbol]:
                            del rewards[symbol]["totals"]
                    self.positions[pool_name]["rewards"] = rewards
            except Exception as e:
                print(f"Error checking rewards for pool {pool_name}: {str(e)}")
        
        # Calculate totals
        for pool_name, pool_data in self.positions.items():
            total_wei = 0
            
            # Add value totals
            for token, value_data in pool_data["value"].items():
                if token == "WETH":
                    total_wei += int(value_data["amount"])
                elif token == "cbETH":
                    quote_result = self.reward_manager._get_quote_with_fallback(
                        value_data.get("address", ""),
                        int(value_data["amount"]),
                        18,
                        "cbETH"
                    )
                    if quote_result:
                        total_wei += int(quote_result["amount"])
            
            # Add reward totals
            for symbol, reward_data in pool_data["rewards"].items():
                if "value" in reward_data and "WETH" in reward_data["value"]:
                    total_wei += int(reward_data["value"]["WETH"]["amount"])
            
            pool_data["totals"] = {
                "wei": str(total_wei),
                "formatted": f"{total_wei/1e18:.6f}"
            }
        
        return self.positions
    
    def process_positions(self, slippage: float = 0.05):
        """
        Process all positions and calculate final values.
        
        Args:
            slippage: Maximum acceptable slippage (default: 0.05 = 5%)
            
        Returns:
            dict: Dictionary containing all positions and totals
        """
        if not self.positions:
            print("\n⚠️ No positions found to process")
            return None
            
        print("\n=== Processing Positions ===")
        
        results = {
            "base": self.positions,
            "totals": {
                "wei": "0",
                "formatted": "0.000000"
            }
        }
        
        # Calculate network total
        network_total = 0
        for pool_data in self.positions.values():
            pool_total = 0
            # Add WETH value
            if "value" in pool_data and "WETH" in pool_data["value"]:
                pool_total += int(pool_data["value"]["WETH"]["amount"])
            # Add cbETH value (converted to WETH)
            if "value" in pool_data and "cbETH" in pool_data["value"]:
                cbeth_amount = int(pool_data["value"]["cbETH"]["amount"])
                # Get conversion rate from conversion_details
                if "conversion_details" in pool_data["value"]["cbETH"]:
                    rate = Decimal(pool_data["value"]["cbETH"]["conversion_details"]["rate"])
                    pool_total += int(cbeth_amount * rate)
            
            # Add rewards value
            if "rewards" in pool_data:
                for reward_symbol, reward_data in pool_data["rewards"].items():
                    if "value" in reward_data and "ETH" in reward_data["value"]:
                        reward_amount = int(reward_data["value"]["ETH"]["amount"])
                        pool_total += reward_amount
            
            # Update pool totals
            pool_data["totals"] = {
                "wei": str(pool_total),
                "formatted": f"{pool_total/1e18:.6f}"
            }
            network_total += pool_total
        
        if network_total > 0:
            results["base"]["totals"] = {
                "wei": str(network_total),
                "formatted": f"{network_total/1e18:.6f}"
            }
            results["totals"] = {
                "wei": str(network_total),
                "formatted": f"{network_total/1e18:.6f}"
            }
        
        return results
    
    def run(self, slippage: float = 0.05):
        """
        Run the complete process.
        
        Args:
            slippage: Maximum acceptable slippage (default: 0.05 = 5%)
            
        Returns:
            dict: Complete processing results including positions and totals
        """
        print("\n=== Curve Position Manager ===")
        print(f"Wallet: {self.wallet_address}")
        print(f"Time: {datetime.now().isoformat()}")
        
        self.check_balances()
        results = self.process_positions(slippage)
        
        print("\n=== Process Complete ===")
        return results

def main():
    """Example usage of the CurveManager."""
    # Get production address from .env
    production_address = os.getenv('PRODUCTION_ADDRESS')
    if not production_address:
        raise ValueError("PRODUCTION_ADDRESS not found in .env file")
    
    try:
        print("\n=== Testing with Production Address ===")
        manager = CurveManager(production_address)
        results = manager.run()

        # Display results
        print("\n=== Results ===")
        print(json.dumps(results, indent=2))
        
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        print("\nFull error traceback:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 