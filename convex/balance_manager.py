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
from .pools import POOLS
from utils.retry import Web3Retry, APIRetry

class ConvexBalanceManager:
    """
    Manages Convex protocol positions and rewards calculation.
    Handles LP token valuation and reward token conversion to ETH.
    """
    
    def __init__(self):
        # Load contract interfaces
        with open(Path(__file__).parent / 'abis/CurveStableSwapNG.json', 'r') as file:
            self.curve_abi = json.load(file)
            
        with open(Path(__file__).parent / 'abis/Gauge.json', 'r') as file:
            self.gauge_abi = json.load(file)
        
        with open(Path(__file__).parent / 'abis/Vyper_contract.json', 'r') as file:
            self.vyper_abi = json.load(file)
        
        # Initialize Web3 connection
        self.w3 = Web3(Web3.HTTPProvider(self.get_rpc_url()))
        
        # Load token configurations
        self.network_tokens = NETWORK_TOKENS
        
    def get_rpc_url(self) -> str:
        """Retrieves Ethereum RPC URL from environment variables"""
        from dotenv import load_dotenv
        import os
        load_dotenv()
        return os.getenv('ETHEREUM_RPC')
        
    def get_balances(self, address: str) -> Dict[str, Any]:
        """Get Convex balances and rewards for address"""
        print("\n" + "="*80)
        print("CONVEX BALANCE MANAGER")
        print("="*80)
        
        checksum_address = Web3.to_checksum_address(address)
        result = {"convex": {"ethereum": {}}}
        total_eth_wei = 0

        # Process each pool
        for pool_name, pool_info in POOLS.items():
            print(f"\nProcessing {pool_name} pool")
            pool_result = self._process_pool(checksum_address, pool_name, pool_info)
            if pool_result:
                result["convex"]["ethereum"][pool_name] = pool_result["convex"]["ethereum"][pool_name]
                total_eth_wei += int(result["convex"]["ethereum"][pool_name]["totals"]["wei"])

        # Add protocol total
        if total_eth_wei > 0:
            result["convex"]["totals"] = {
                "wei": total_eth_wei,
                "formatted": f"{total_eth_wei/1e18:.6f}"
            }

        return result

    def _process_pool(self, address: str, pool_name: str, pool_info: Dict) -> Dict[str, Any]:
        """Process pool positions and rewards"""
        try:
            # Initialize gauge contract
            gauge_contract = self.w3.eth.contract(
                address=pool_info['gauge'],
                abi=self.gauge_abi
            )
            
            # Get LP token balance from gauge
            print("\naccount (address)")
            print(f"{address}")
            print("uint256")
            print("\n[ balanceOf(address) method Response ]")
            lp_balance = Web3Retry.call_contract_function(
                gauge_contract.functions.balanceOf(address).call
            )
            print(f"    uint256 :  {lp_balance}")

            if lp_balance == 0:
                print(f"[Convex] No LP balance found for {pool_name}")
                return None

            # Determine which ABI to use
            is_vyper = pool_info['abis']['pool'] == "Vyper_contract.json"
            pool_abi = self.vyper_abi if is_vyper else self.curve_abi

            # Initialize pool contract with correct ABI
            curve_pool = self.w3.eth.contract(
                address=pool_info['pool'],
                abi=pool_abi
            )

            # Calculate share of pool
            print("\nQuerying Curve pool contract for total supply:")
            print(f"  Contract: {pool_info['pool']}")
            print("  Function: totalSupply() - Returns total LP tokens in Curve pool")
            total_supply = Web3Retry.call_contract_function(
                curve_pool.functions.totalSupply().call
            )
            ratio = lp_balance / total_supply if total_supply > 0 else 0
            print(f"\n[Convex] Calculating pool share:")
            print(f"  User LP balance: {lp_balance}")
            print(f"  Total LP supply: {total_supply}")
            print(f"  Share ratio: {ratio:.6%}")

            # Process underlying tokens
            print("\n[Convex] Processing underlying tokens...")
            print("\nQuerying Curve pool contract:")
            print(f"  Contract: {pool_info['pool']}")
            
            # Determine if we're using Vyper contract
            is_vyper = pool_info['abis']['pool'] == "Vyper_contract.json"
            
            if is_vyper:
                print("  Function: get_balances() - Returns balances of all tokens in pool")
                pool_balances = Web3Retry.call_contract_function(
                    curve_pool.functions.get_balances().call
                )
                n_coins = len(pool_balances)
            else:
                print("  Function: N_COINS() - Returns number of tokens in pool")
                n_coins = Web3Retry.call_contract_function(
                    curve_pool.functions.N_COINS().call
                )
            
            print(f"Number of tokens in pool: {n_coins}")
            lp_balances = {}
            lp_total = 0

            for i in range(n_coins):
                print(f"\nQuerying token information for index {i}:")
                print("  Function: coins(uint256) - Returns token address")
                coin_address = Web3Retry.call_contract_function(
                    curve_pool.functions.coins(i).call
                )
                
                if is_vyper:
                    pool_balance = pool_balances[i]
                else:
                    print("  Function: balances(uint256) - Returns token balance in pool")
                    pool_balance = Web3Retry.call_contract_function(
                        curve_pool.functions.balances(i).call
                    )

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

                token_data = {
                    "amount": balance,
                    "decimals": decimals
                }

                if symbol == "WETH":
                    print("  Converting WETH: Direct 1:1 conversion")
                    token_data["value"] = {
                        "ETH": {
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
                    }
                    token_data["totals"] = {
                        "wei": balance,
                        "formatted": f"{balance/1e18:.6f}"
                    }
                    lp_total += balance
                else:
                    print(f"  Converting {symbol}: Using CoWSwap for price discovery")
                    quote_result = self.get_quote_with_fallback(
                        coin_address, balance, decimals, symbol
                    )
                    if quote_result:
                        eth_value = quote_result["amount"]
                        print(f"  → {eth_value/1e18:.6f} ETH")
                        token_data["value"] = {
                            "ETH": quote_result
                        }
                        token_data["totals"] = {
                            "wei": eth_value,
                            "formatted": f"{eth_value/1e18:.6f}"
                        }
                        lp_total += eth_value

                lp_balances[symbol] = token_data

            # Process rewards
            print("\n[Convex] Processing reward tokens...")
            print("\nQuerying gauge contract for earned rewards:")
            print(f"  Contract: {pool_info['gauge']}")
            print("  Function: earned(address) - Returns unclaimed rewards")
            
            # Get reward token address
            reward_token_address = Web3Retry.call_contract_function(
                gauge_contract.functions.rewardToken().call
            )
            
            # Get earned amount
            earned_amount = Web3Retry.call_contract_function(
                gauge_contract.functions.earned(address).call
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
                
                reward_data = {
                    "amount": earned_amount,
                    "decimals": decimals
                }
                
                print(f"\nConverting {symbol} rewards to ETH:")
                quote_result = self.get_quote_with_fallback(
                    reward_token_address, earned_amount, decimals, symbol
                )
                if quote_result:
                    eth_value = quote_result["amount"]
                    print(f"  → {eth_value/1e18:.6f} ETH")
                    reward_data["value"] = {
                        "ETH": quote_result
                    }
                    reward_data["totals"] = {
                        "wei": eth_value,
                        "formatted": f"{eth_value/1e18:.6f}"
                    }
                    rewards_total += eth_value
                
                rewards[symbol] = reward_data

            # Calculate total ETH value
            total_eth_value = lp_total + rewards_total

            print("\n[Convex] Calculation complete")
            
            # Afficher les LP tokens
            for token_symbol, token_data in lp_balances.items():
                if "totals" in token_data:
                    amount = token_data["totals"]["wei"]
                    if amount > 0:
                        print(f"convex.ethereum.{pool_name}.{token_symbol}: {amount/1e18:.6f} ETH")

            # Afficher les rewards
            for token_symbol, reward_data in rewards.items():
                if "totals" in reward_data:
                    amount = reward_data["totals"]["wei"]
                    if amount > 0:
                        print(f"convex.ethereum.{pool_name}.rewards.{token_symbol}: {amount/1e18:.6f} ETH")

            return {
                "convex": {
                    "ethereum": {
                        pool_name: {
                            "amount": str(lp_balance),
                            "decimals": 18,
                            "value": lp_balances,
                            "rewards": rewards,
                            "totals": {
                                "wei": total_eth_value,
                                "formatted": f"{total_eth_value/1e18:.6f}"
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
        Gets ETH conversion quote for tokens.
        Uses the centralized quote logic from cow_client.py
        """
        print(f"\nAttempting to get quote for {symbol}:")
        
        result = get_quote(
            network="ethereum",
            sell_token=token_address,
            buy_token=self.network_tokens["ethereum"]["WETH"]["address"],
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