from web3 import Web3
import json
from pathlib import Path
from decimal import Decimal
from typing import Dict, Any
import sys
import time

# Add parent directory to path to import config
sys.path.append(str(Path(__file__).parent.parent))

from config.networks import NETWORK_TOKENS, RPC_URLS
from cowswap.cow_client import get_quote
from utils.retry import Web3Retry, APIRetry

# Import POOL_INFO with proper path handling
try:
    from .pools import POOL_INFO
except ImportError:
    # Fallback for when running as standalone script
    from pools import POOL_INFO

class ConvexBalanceManager:
    """
    Manages Convex protocol positions and rewards calculation.
    Handles LP token valuation and reward token conversion to WETH.
    """
    
    def __init__(self, network: str = "ethereum"):
        # Set network
        self.network = network
        
        # Load contract interfaces
        with open(Path(__file__).parent / 'abis/CurveStableSwapNG.json', 'r') as file:
            self.curve_abi = json.load(file)
            
        with open(Path(__file__).parent / 'abis/Gauge.json', 'r') as file:
            self.gauge_abi = json.load(file)
        
        # Initialize Web3 connection
        self.w3 = Web3(Web3.HTTPProvider(self.get_rpc_url()))
        
        # Load token configurations
        self.network_tokens = NETWORK_TOKENS
        
    def get_rpc_url(self) -> str:
        """Retrieves RPC URL from environment variables based on network"""
        from dotenv import load_dotenv
        import os
        load_dotenv()
        
        # Get RPC URL based on network
        if self.network == "ethereum":
            return os.getenv('ETHEREUM_RPC')
        elif self.network == "base":
            return os.getenv('BASE_RPC')
        else:
            raise ValueError(f"Unsupported network: {self.network}")
        
    def get_balances(self, address: str) -> Dict[str, Any]:
        """Get Convex balances and rewards for address"""
        print("\n" + "="*80)
        print("CONVEX BALANCE MANAGER")
        print("="*80)
        
        checksum_address = Web3.to_checksum_address(address)
        result = {"convex": {self.network: {}}}
        total_weth_wei = 0
        network_total = 0

        # Process WETH/tacETH pool
        print("\nProcessing WETH/tacETH pool")
        weth_taceth_result = self._process_weth_taceth_pool(checksum_address)
        if weth_taceth_result:
            result["convex"][self.network]["WETH/tacETH"] = weth_taceth_result["convex"][self.network]["WETH/tacETH"]
            position_total = int(result["convex"][self.network]["WETH/tacETH"]["totals"]["wei"])
            network_total += position_total

        # Add network total
        if network_total > 0:
            result["convex"][self.network]["totals"] = {
                "wei": network_total,
                "formatted": f"{network_total/1e18:.6f}"
            }
            # Add protocol total (same as network total for now since we only have one network)
            result["convex"]["totals"] = {
                "wei": network_total,
                "formatted": f"{network_total/1e18:.6f}"
            }

        return result

    def _process_weth_taceth_pool(self, address: str) -> Dict[str, Any]:
        """Process WETH/tacETH pool positions and rewards"""
        try:
            # Pool info
            pool_name = POOL_INFO["name"]
            lp_token_address = POOL_INFO["lp_token"]
            deposit_contract_address = POOL_INFO["deposit_contract"]
            rewards_contract_address = POOL_INFO["rewards_contract"]
            
            print(f"\nPool information:")
            print(f"  Pool: {pool_name}")
            print(f"  LP Token: {lp_token_address}")
            print(f"  Deposit Contract: {deposit_contract_address}")
            print(f"  Rewards Contract: {rewards_contract_address}")
            
            # Initialize contracts
            lp_token_contract = self.w3.eth.contract(
                address=lp_token_address,
                abi=self.curve_abi
            )
            
            rewards_contract = self.w3.eth.contract(
                address=rewards_contract_address,
                abi=self.gauge_abi
            )
            
            # Get LP token balance from rewards contract
            print(f"\nQuerying rewards contract for LP balance:")
            print(f"  Contract: {rewards_contract_address}")
            print(f"  Function: balanceOf(address) - Returns LP tokens staked by user")
            lp_balance = Web3Retry.call_contract_function(
                rewards_contract.functions.balanceOf(address).call
            )
            print(f"  LP Balance: {lp_balance}")

            if lp_balance == 0:
                print(f"[Convex] No LP balance found for {pool_name}")
                return None

            # Get total supply of LP tokens
            print(f"\nQuerying LP token contract for total supply:")
            print(f"  Contract: {lp_token_address}")
            print(f"  Function: totalSupply() - Returns total LP tokens")
            total_supply = Web3Retry.call_contract_function(
                lp_token_contract.functions.totalSupply().call
            )
            
            ratio = lp_balance / total_supply if total_supply > 0 else 0
            print(f"\n[Convex] Calculating pool share:")
            print(f"  User LP balance: {lp_balance}")
            print(f"  Total LP supply: {total_supply}")
            print(f"  Share ratio: {ratio:.6%}")

            # Process underlying tokens (WETH and tacETH)
            print(f"\n[Convex] Processing underlying tokens...")
            print(f"\nQuerying LP token contract:")
            print(f"  Contract: {lp_token_address}")
            print(f"  Function: N_COINS() - Returns number of tokens in pool")
            
            # For WETH/tacETH pool, we know there are 2 tokens
            n_coins = 2
            print(f"Number of tokens in pool: {n_coins}")
            
            lp_balances = {}
            lp_total = 0

            # Get token addresses and balances
            token_addresses = []
            token_balances = []
            
            for i in range(n_coins):
                print(f"\nQuerying token information for index {i}:")
                print("  Function: coins(uint256) - Returns token address")
                coin_address = Web3Retry.call_contract_function(
                    lp_token_contract.functions.coins(i).call
                )
                token_addresses.append(coin_address)
                
                print("  Function: balances(uint256) - Returns token balance in pool")
                pool_balance = Web3Retry.call_contract_function(
                    lp_token_contract.functions.balances(i).call
                )
                token_balances.append(pool_balance)

                # Get token info
                token_contract = self.w3.eth.contract(
                    address=coin_address,
                    abi=self.curve_abi
                )
                print("  Querying token contract:")
                print("    Function: symbol() - Returns token symbol")
                symbol = Web3Retry.call_contract_function(
                    token_contract.functions.symbol().call
                )
                print("    Function: decimals() - Returns token decimals")
                decimals = Web3Retry.call_contract_function(
                    token_contract.functions.decimals().call
                )

                print(f"\nProcessing {symbol}:")
                print(f"  Total in pool: {pool_balance / 10**decimals:.6f} {symbol}")

                balance = int(pool_balance * ratio)
                formatted_balance = balance / 10**decimals
                print(f"  User share: {formatted_balance:.6f} {symbol} ({balance} wei)")

                # Convert to WETH
                if symbol == "WETH":
                    print("  Converting WETH: Direct 1:1 conversion")
                    token_data = {
                        "amount": balance,
                        "decimals": decimals,
                        "value": {
                            "WETH": {
                                "amount": balance,
                                "decimals": decimals,
                                "conversion_details": {
                                    "source": "Direct",
                                    "price_impact": "0.0000%",
                                    "rate": "1.000000",
                                    "fee_percentage": "0.0000%",
                                    "fallback": False,
                                    "note": "Direct 1:1 conversion"
                                }
                            }
                        },
                        "totals": {
                            "wei": balance,
                            "formatted": f"{balance/1e18:.6f}"
                        }
                    }
                    lp_total += balance
                else:
                    print(f"  Converting {symbol}: Using CoWSwap for price discovery")
                    quote_result = self.get_quote_with_fallback(
                        coin_address, balance, decimals, symbol
                    )
                    if quote_result:
                        weth_value = quote_result["amount"]
                        print(f"  → {weth_value/1e18:.6f} WETH")
                        token_data = {
                            "amount": balance,
                            "decimals": decimals,
                            "value": {
                                "WETH": quote_result
                            },
                            "totals": {
                                "wei": weth_value,
                                "formatted": f"{weth_value/1e18:.6f}"
                            }
                        }
                        lp_total += weth_value
                    else:
                        token_data = {
                            "amount": balance,
                            "decimals": decimals,
                            "value": {
                                "WETH": {
                                    "amount": 0,
                                    "decimals": 18,
                                    "conversion_details": {
                                        "source": "Failed",
                                        "price_impact": "0.0000%",
                                        "rate": "0.000000",
                                        "fee_percentage": "0.0000%",
                                        "fallback": False,
                                        "note": "Conversion failed"
                                    }
                                }
                            },
                            "totals": {
                                "wei": 0,
                                "formatted": "0.000000"
                            }
                        }

                lp_balances[symbol] = token_data

            # Process rewards
            print(f"\n[Convex] Processing reward tokens...")
            print(f"\nQuerying rewards contract for earned rewards:")
            print(f"  Contract: {rewards_contract_address}")
            print(f"  Function: earned(address) - Returns unclaimed rewards")
            
            # Get reward token address
            reward_token_address = Web3Retry.call_contract_function(
                rewards_contract.functions.rewardToken().call
            )
            
            # Get earned amount
            earned_amount = Web3Retry.call_contract_function(
                rewards_contract.functions.earned(address).call
            )
            
            rewards = {}
            rewards_total = 0
            
            if earned_amount > 0:
                token_contract = self.w3.eth.contract(
                    address=reward_token_address,
                    abi=self.curve_abi
                )
                symbol = Web3Retry.call_contract_function(
                    token_contract.functions.symbol().call
                )
                decimals = Web3Retry.call_contract_function(
                    token_contract.functions.decimals().call
                )
                
                print(f"\nUnclaimed rewards:")
                print(f"  • {symbol}:")
                print(f"    Address: {reward_token_address}")
                print(f"    Amount: {earned_amount / 10**decimals:.6f} ({earned_amount} wei)")
                print(f"    Decimals: {decimals}")
                
                print(f"\nConverting {symbol} rewards to WETH:")
                quote_result = self.get_quote_with_fallback(
                    reward_token_address, earned_amount, decimals, symbol
                )
                if quote_result:
                    weth_value = quote_result["amount"]
                    print(f"  → {weth_value/1e18:.6f} WETH")
                    reward_data = {
                        "amount": str(earned_amount),
                        "decimals": decimals,
                        "value": {
                            "WETH": {
                                "amount": weth_value,
                                "decimals": 18,
                                "conversion_details": quote_result["conversion_details"]
                            }
                        }
                    }
                    rewards_total += weth_value
                else:
                    reward_data = {
                        "amount": str(earned_amount),
                        "decimals": decimals,
                        "value": {
                            "WETH": {
                                "amount": 0,
                                "decimals": 18,
                                "conversion_details": {
                                    "source": "Failed",
                                    "price_impact": "0.0000%",
                                    "rate": "0.000000",
                                    "fee_percentage": "0.0000%",
                                    "fallback": False,
                                    "note": "Conversion failed"
                                }
                            }
                        }
                    }
                
                rewards[symbol] = reward_data

            # Calculate total WETH value
            total_weth_value = lp_total + rewards_total

            print(f"\n[Convex] Calculation complete")
            
            # Display LP tokens
            for token_symbol, token_data in lp_balances.items():
                if "totals" in token_data:
                    amount = token_data["totals"]["wei"]
                    if amount > 0:
                        print(f"convex.ethereum.{pool_name}.{token_symbol}: {amount/1e18:.6f} WETH")

            # Display rewards
            for token_symbol, reward_data in rewards.items():
                if "value" in reward_data and "WETH" in reward_data["value"]:
                    amount = reward_data["value"]["WETH"]["amount"]
                    if amount > 0:
                        print(f"convex.ethereum.{pool_name}.rewards.{token_symbol}: {amount/1e18:.6f} WETH")

            return {
                "convex": {
                    self.network: {
                        pool_name: {
                            "amount": str(lp_balance),
                            "decimals": 18,
                            "value": lp_balances,
                            "rewards": rewards,
                            "totals": {
                                "wei": total_weth_value,
                                "formatted": f"{total_weth_value/1e18:.6f}"
                            }
                        }
                    }
                }
            }

        except Exception as e:
            print(f"[Convex] Error processing {pool_name}: {str(e)}")
            return None

    def get_quote_with_fallback(self, token_address: str, amount: int, decimals: int, symbol: str) -> Dict[str, Any]:
        """
        Gets WETH conversion quote for tokens.
        Uses the centralized quote logic from cow_client.py
        """
        print(f"\nAttempting to get quote for {symbol}:")
        
        network = self.network
        sell_token = token_address
        buy_token = self.network_tokens[self.network]["WETH"]["address"]
        
        result = get_quote(
            network=network,
            sell_token=sell_token,
            buy_token=buy_token,
            amount=str(int(amount)),
            token_decimals=decimals,
            token_symbol=symbol
        )

        if result["quote"]:
            return {
                "amount": int(result["quote"]["quote"]["buyAmount"]),
                "decimals": 18,
                "conversion_details": result["conversion_details"]
            }
        
        return {
            "amount": 0,
            "decimals": 18,
            "conversion_details": result["conversion_details"]
        }

    def _calculate_weth_totals(self, lp_tokens: Dict, rewards: Dict) -> Dict[str, int]:
        """
        Calculate WETH totals for LP tokens and rewards
        """
        # WETH total from LP tokens
        lp_total = 0
        for token_data in lp_tokens.values():
            if "value" in token_data and "WETH" in token_data["value"]:
                lp_total += token_data["value"]["WETH"]["amount"]
        
        # WETH total from rewards
        rewards_total = 0
        for reward_data in rewards.values():
            if "value" in reward_data and "WETH" in reward_data["value"]:
                rewards_total += reward_data["value"]["WETH"]["amount"]
        
        # Combined total
        total = lp_total + rewards_total
        
        return {
            "lp_tokens_total": {
                "wei": lp_total,
                "formatted": f"{lp_total/10**18:.6f}"
            },
            "rewards_total": {
                "wei": rewards_total,
                "formatted": f"{rewards_total/10**18:.6f}"
            },
            "total": {
                "wei": total,
                "formatted": f"{total/10**18:.6f}"
            }
        }



if __name__ == "__main__":
    import sys
    
    # Production address
    PRODUCTION_ADDRESS = "0x66DbceE7feA3287B3356227d6F3DfF3CeFbC6F3C"
    
    # Get address from command line argument or use production address
    address = sys.argv[1] if len(sys.argv) > 1 else PRODUCTION_ADDRESS
    
    # Create manager instance
    manager = ConvexBalanceManager()
    
    # Get balances
    balances = manager.get_balances(address)
    
    # Display final result
    print("\n" + "="*80)
    print("FINAL RESULT:")
    print("="*80 + "\n")
    print(json.dumps(balances, indent=2)) 