"""
Master script to manage Equilibria positions, balances, and conversions.
"""
import json
from pathlib import Path
from typing import Dict, List, Optional
from decimal import Decimal
from web3 import Web3
import sys
from datetime import datetime
import os
from dotenv import load_dotenv

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from config.networks import RPC_URLS, NETWORK_TOKENS
from pendle.sdk.remove_liquidity import remove_liquidity
from equilibria.balance.check_balances import get_equilibria_lp_balances
from equilibria.balance.stake_balance import StakeBalance
from equilibria.balance.rewards_balance import RewardsBalance
from cowswap.cow_client import get_cowswap_quote

# Load environment variables
load_dotenv()

def format_amount(wei_str):
    """Format wei amount to ETH with 6 decimals."""
    try:
        # Si c'est déjà en ETH (contient un point)
        if '.' in str(wei_str):
            return f"{float(wei_str):,.6f}"
        # Sinon c'est en wei
        eth = float(wei_str) / 1e18
        return f"{eth:,.6f}"
    except Exception as e:
        print(f"Warning: Error formatting amount {wei_str}: {e}")
        return str(wei_str)

class EquilibriaManager:
    def __init__(self, wallet_address: str):
        """
        Initialize the EquilibriaManager.
        
        Args:
            wallet_address: The wallet address to manage positions for
        """
        self.wallet_address = wallet_address
        self.positions = {}
        self.stake_balances = {}
        self.rewards_balances = {}
        
    def check_balances(self):
        """Check all LP token balances, staked balances, and rewards across all networks."""
        print("\n=== Checking Balances ===")
        self.positions = {}
        
        # First check staked balances
        print("\nChecking staked balances...")
        stake_balance = StakeBalance()
        self.stake_balances = stake_balance.get_staked_balance(self.wallet_address)
        
        # Check rewards
        print("\nChecking rewards...")
        rewards_balance = RewardsBalance()
        self.rewards_balances = rewards_balance.get_rewards_balance(self.wallet_address)
        
        # Check LP balances on each network
        for network, rpc_url in RPC_URLS.items():
            print(f"\nNetwork: {network}")
            w3 = Web3(Web3.HTTPProvider(rpc_url))
            chain_id = "1" if network == "ethereum" else "8453" if network == "base" else None
            
            if chain_id is None:
                print(f"⚠️ Unsupported network: {network}")
                continue
                
            # Get LP balances
            lp_balances = get_equilibria_lp_balances(w3, self.wallet_address, chain_id)
            
            for market_address, balance in lp_balances.items():
                if balance > 0:
                    if market_address not in self.positions:
                        self.positions[market_address] = {"lp": balance}
                    else:
                        self.positions[market_address]["lp"] = balance
                    print(f"✓ Found {balance} LP tokens in market {market_address}")
        
        # Print summary of positions found
        if self.positions or any(self.stake_balances.values()) or any(self.rewards_balances.values()):
            print("\n=== Positions Found ===")
            
            # Print staked positions
            if any(self.stake_balances.values()):
                print("\nStaked Positions:")
                for network, pools in self.stake_balances.items():
                    if pools:
                        print(f"\n{network.upper()}:")
                        for pool_name, data in pools.items():
                            print(f"  {pool_name}: {data['balance_in_eth']} LP tokens")
                            print(f"  Market: {data['market_address']}")
                            print(f"  Pool: {data['base_reward_pool']}")
            
            # Print LP positions
            if self.positions:
                print("\nLP Positions:")
                for market_address, balances in self.positions.items():
                    print(f"\nMarket: {market_address}")
                    if balances["lp"] > 0:
                        print(f"  LP Balance: {balances['lp']} LP tokens")
            
            # Print rewards
            if any(self.rewards_balances.values()):
                print("\nRewards:")
                for network, pools in self.rewards_balances.items():
                    if pools:
                        print(f"\n{network.upper()}:")
                        for pool_name, data in pools.items():
                            print(f"  {pool_name}:")
                            print(f"  Market: {data['market_address']}")
                            print(f"  Pool: {data['base_reward_pool']}")
                            print("  Rewards:")
                            for token_address, reward_data in data['rewards'].items():
                                token_symbol = reward_data.get('symbol', token_address[:8])
                                print(f"    {token_symbol}:")
                                print(f"      Amount: {Web3.from_wei(int(reward_data['amount']), 'ether')} tokens")
                                if 'value' in reward_data and 'WETH' in reward_data['value']:
                                    weth_amount = reward_data['value']['WETH']['amount']
                                    print(f"      Value: {format_amount(weth_amount)} WETH")
                                    print(f"      Conversion: {reward_data['value']['WETH']['conversion_details']['note']}")
        else:
            print("\n⚠️ No positions found")
        
        return {
            "positions": self.positions,
            "stake_balances": self.stake_balances,
            "rewards": self.rewards_balances
        }
        
    def process_positions(self, slippage: float = 0.05):
        """
        Process all positions by removing liquidity and converting rewards.
        
        Args:
            slippage: Maximum acceptable slippage (default: 0.05 = 5%)
            
        Returns:
            dict: Dictionary containing all positions and totals
        """
        if not self.positions and not any(self.stake_balances.values()) and not any(self.rewards_balances.values()):
            print("\n⚠️ No positions found to process")
            return None
            
        print("\n=== Processing Positions ===")
        
        # Structure to store all results
        results = {
            "ethereum": {},
            "base": {}
        }
        
        # Process staked positions first
        for network, pools in self.stake_balances.items():
            for pool_name, data in pools.items():
                market_address = data['market_address']
                balance = data['balance']
                print(f"\nProcessing staked position in {pool_name}")
                print(f"Market: {market_address}")
                print(f"Balance: {data['balance_in_eth']} ETH")
                
                try:
                    stake_result = remove_liquidity(
                        market_address=market_address,
                        amount=balance,  # Already in wei from stake_balance
                        receiver=self.wallet_address,
                        slippage=slippage
                    )
                    
                    # Get the final WETH amount from the last conversion step
                    last_step = stake_result["conversion_steps"][-1]
                    weth_amount = Decimal(last_step["to"]["amount"].replace(",", ""))
                    
                    # Add position to results
                    results[network][pool_name] = {
                        "staking_contract": data['base_reward_pool'],
                        "amount": str(balance),
                        "decimals": 18,
                        "value": {
                            "WETH": {
                                "amount": str(int(weth_amount * Decimal('1e18'))),
                                "decimals": 18,
                                "conversion_details": {
                                    "source": "Pendle SDK",
                                    "price_impact": last_step.get("price_impact", "0.0000"),
                                    "rate": str(weth_amount / (Decimal(balance) / Decimal('1e18'))),
                                    "fee_percentage": "0.0000%",
                                    "fallback": False,
                                    "note": "Direct Conversion using Pendle SDK"
                                }
                            }
                        },
                        "rewards": {},
                        "totals": {
                            "wei": str(int(weth_amount * Decimal('1e18'))),
                            "formatted": format_amount(str(weth_amount))
                        }
                    }
                    
                except Exception as e:
                    print(f"✗ Error removing liquidity from staked position: {str(e)}")
        
        # Process LP positions
        for market_address, position_data in self.positions.items():
            network = "ethereum" if market_address.startswith("0x") else "base"
            print(f"\nProcessing LP position in market: {market_address}")
            
            # Process LP tokens
            if position_data["lp"] > 0:
                try:
                    lp_result = remove_liquidity(
                        market_address=market_address,
                        amount=int(position_data["lp"] * Decimal('1e18')),  # Convert to wei
                        receiver=self.wallet_address,
                        slippage=slippage
                    )
                    
                    # Get the final WETH amount from the last conversion step
                    last_step = lp_result["conversion_steps"][-1]
                    weth_amount = Decimal(last_step["to"]["amount"].replace(",", ""))
                    
                    # Add position to results
                    market_name = f"LP-{market_address[:8]}"
                    if market_name not in results[network]:
                        results[network][market_name] = {
                            "staking_contract": "LP",
                            "amount": str(int(position_data["lp"] * Decimal('1e18'))),
                            "decimals": 18,
                            "value": {
                                "WETH": {
                                    "amount": str(int(weth_amount * Decimal('1e18'))),
                                    "decimals": 18,
                                    "conversion_details": {
                                        "source": "Pendle SDK",
                                        "price_impact": last_step.get("price_impact", "0.0000"),
                                        "rate": str(weth_amount / position_data["lp"]),
                                        "fee_percentage": "0.0000%",
                                        "fallback": False,
                                        "note": "Direct Conversion using Pendle SDK"
                                    }
                                }
                            },
                            "rewards": {},
                            "totals": {
                                "wei": str(int(weth_amount * Decimal('1e18'))),
                                "formatted": format_amount(str(weth_amount))
                            }
                        }
                    else:
                        # If we already have a position for this market, add to it
                        current_amount = Decimal(results[network][market_name]["amount"]) / Decimal('1e18')
                        new_amount = current_amount + position_data["lp"]
                        current_weth = Decimal(results[network][market_name]["value"]["WETH"]["amount"]) / Decimal('1e18')
                        new_weth = current_weth + weth_amount
                        
                        results[network][market_name].update({
                            "amount": str(int(new_amount * Decimal('1e18'))),
                            "value": {
                                "WETH": {
                                    "amount": str(int(new_weth * Decimal('1e18'))),
                                    "decimals": 18,
                                    "conversion_details": {
                                        "source": "Pendle SDK",
                                        "price_impact": last_step.get("price_impact", "0.0000"),
                                        "rate": str(new_weth / new_amount),
                                        "fee_percentage": "0.0000%",
                                        "fallback": False,
                                        "note": "Direct Conversion using Pendle SDK"
                                    }
                                }
                            },
                            "totals": {
                                "wei": str(int(new_weth * Decimal('1e18'))),
                                "formatted": format_amount(str(new_weth))
                            }
                        })
                    
                except Exception as e:
                    print(f"✗ Error removing liquidity from LP position: {str(e)}")

        # Process rewards
        for network, pools in self.rewards_balances.items():
            for pool_name, data in pools.items():
                print(f"\nProcessing rewards for {pool_name}")
                
                for token_address, reward_data in data['rewards'].items():
                    try:
                        # Get token symbol from config
                        token_symbol = "UNKNOWN"
                        for token_name, token_info in NETWORK_TOKENS[network].items():
                            if token_info['address'].lower() == token_address.lower():
                                token_symbol = token_name
                                break

                        print(f"\nProcessing rewards for {pool_name} - {token_symbol}")
                        
                        # Get WETH address for the current network
                        weth_address = NETWORK_TOKENS[network]['WETH']['address']
                        
                        # Get CowSwap quote for reward token to WETH
                        cowswap_result = get_cowswap_quote(
                            network=network,
                            sell_token=token_address,
                            buy_token=weth_address,
                            amount=str(reward_data['amount']),
                            sell_decimals=18,
                            buy_decimals=18
                        )
                        
                        if not cowswap_result:
                            print(f"⚠️ No CowSwap quote available for {token_address}")
                            continue

                        if not isinstance(cowswap_result, dict) or 'quote' not in cowswap_result:
                            print(f"⚠️ Invalid CowSwap response format for {token_address}")
                            continue

                        quote_data = cowswap_result['quote']
                        if not isinstance(quote_data, dict) or 'quote' not in quote_data:
                            print(f"⚠️ Invalid CowSwap quote format for {token_address}")
                            continue

                        quote = quote_data['quote']
                        if not isinstance(quote, dict) or 'buyAmount' not in quote:
                            print(f"⚠️ No buyAmount in CowSwap quote for {token_address}")
                            continue

                        weth_amount = Decimal(quote['buyAmount']) / Decimal('1e18')
                        print(f"✓ Converted to {weth_amount} WETH")
                            
                        # Add rewards to results
                        if pool_name in results[network]:
                            # Add rewards to existing pool
                            results[network][pool_name]["rewards"][token_symbol] = {
                                "amount": str(reward_data['amount']),
                                "decimals": 18,
                                "value": {
                                    "WETH": {
                                        "amount": str(int(weth_amount * Decimal('1e18'))),
                                        "decimals": 18,
                                        "conversion_details": cowswap_result.get('conversion_details', {
                                            "source": "CoWSwap",
                                            "price_impact": "0",
                                            "rate": str(weth_amount / (Decimal(reward_data['amount']) / Decimal('1e18'))),
                                            "fee_percentage": "0",
                                            "fallback": False,
                                            "note": "Direct CoWSwap quote"
                                        })
                                    }
                                }
                            }
                            
                            # Update pool totals
                            current_total = Decimal(results[network][pool_name]["totals"]["wei"]) / Decimal('1e18')
                            new_total = current_total + weth_amount
                            results[network][pool_name]["totals"] = {
                                "wei": str(int(new_total * Decimal('1e18'))),
                                "formatted": format_amount(str(new_total))
                            }
                        else:
                            # Create new pool entry with rewards
                            results[network][pool_name] = {
                                "staking_contract": data['base_reward_pool'],
                                "amount": "0",
                                "decimals": 18,
                                "value": {},
                                "rewards": {
                                    token_symbol: {
                                        "amount": str(reward_data['amount']),
                                        "decimals": 18,
                                        "value": {
                                            "WETH": {
                                                "amount": str(int(weth_amount * Decimal('1e18'))),
                                                "decimals": 18,
                                                "conversion_details": cowswap_result.get('conversion_details', {
                                                    "source": "CoWSwap",
                                                    "price_impact": "0",
                                                    "rate": str(weth_amount / (Decimal(reward_data['amount']) / Decimal('1e18'))),
                                                    "fee_percentage": "0",
                                                    "fallback": False,
                                                    "note": "Direct CoWSwap quote"
                                                })
                                            }
                                        }
                                    }
                                },
                                "totals": {
                                    "wei": str(int(weth_amount * Decimal('1e18'))),
                                    "formatted": format_amount(str(weth_amount))
                                }
                            }
                            
                    except Exception as e:
                        print(f"✗ Error processing rewards for token {token_address}: {str(e)}")
        
        # Calculate network totals
        for network in ["ethereum", "base"]:
            if network in results:
                network_total = Decimal('0')
                for pool_name, pool_data in results[network].items():
                    if pool_name != "totals":
                        pool_total = Decimal('0')
                        
                        # Add main position value
                        if "value" in pool_data and "WETH" in pool_data["value"]:
                            pool_total += Decimal(pool_data["value"]["WETH"]["amount"]) / Decimal('1e18')
                        
                        # Add rewards value
                        if "rewards" in pool_data:
                            for reward_symbol, reward_data in pool_data["rewards"].items():
                                if "value" in reward_data and "WETH" in reward_data["value"]:
                                    reward_amount = Decimal(reward_data["value"]["WETH"]["amount"]) / Decimal('1e18')
                                    pool_total += reward_amount
                        
                        # Update pool totals
                        results[network][pool_name]["totals"] = {
                            "wei": str(int(pool_total * Decimal('1e18'))),
                            "formatted": format_amount(str(pool_total))
                        }
                        
                        network_total += pool_total
                
                if network_total > 0:
                    results[network]["totals"] = {
                        "wei": str(int(network_total * Decimal('1e18'))),
                        "formatted": format_amount(str(network_total))
                    }
        
        # Calculate global total
        global_total = Decimal('0')
        for network in ["ethereum", "base"]:
            if network in results and "totals" in results[network]:
                global_total += Decimal(results[network]["totals"]["wei"]) / Decimal('1e18')
        
        if global_total > 0:
            results["totals"] = {
                "wei": str(int(global_total * Decimal('1e18'))),
                "formatted": format_amount(str(global_total))
            }
        
        # Clean up empty networks
        for network in ["ethereum", "base"]:
            if network in results and not results[network]:
                del results[network]
        
        return results
    
    def run(self, slippage: float = 0.05):
        """
        Run the complete process.
        
        Args:
            slippage: Maximum acceptable slippage (default: 0.05 = 5%)
            
        Returns:
            dict: Complete processing results including positions and totals
        """
        print("\n=== Equilibria Position Manager ===")
        print(f"Wallet: {self.wallet_address}")
        print(f"Time: {datetime.now().isoformat()}")
        
        self.check_balances()
        results = self.process_positions(slippage)
        
        print("\n=== Process Complete ===")
        return results

def main():
    """Example usage of the EquilibriaManager."""
    # Get production address from .env
    production_address = os.getenv('PRODUCTION_ADDRESS')
    if not production_address:
        raise ValueError("PRODUCTION_ADDRESS not found in .env file")
    
    try:
        print("\n=== Testing with Production Address ===")
        manager = EquilibriaManager(production_address)
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
