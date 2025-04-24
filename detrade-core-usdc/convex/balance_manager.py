from web3 import Web3
import json
from pathlib import Path
from decimal import Decimal
from typing import Dict, Any
import sys
import time

# Add parent directory to path to import config
sys.path.append(str(Path(__file__).parent.parent))

from config.networks import NETWORK_TOKENS
from cowswap.cow_client import get_quote
from .USDCfxUSD.constants import POOL_INFO, DEDICATED_VAULTS

class ConvexBalanceManager:
    """
    Manages Convex protocol positions and rewards calculation.
    Handles LP token valuation and reward token conversion to USDC.
    """
    
    def __init__(self):
        self.POOL_INFO = POOL_INFO
        self.DEDICATED_VAULTS = DEDICATED_VAULTS
        
        # Load contract interfaces
        with open(Path(__file__).parent / 'USDCfxUSD/abis/StakingProxyERC20.json', 'r') as file:
            self.staking_abi = json.load(file)
            
        with open(Path(__file__).parent / 'USDCfxUSD/abis/CurveStableSwapNG.json', 'r') as file:
            self.curve_abi = json.load(file)
        
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
        
        # Check if user has a dedicated vault
        checksum_address = Web3.to_checksum_address(address)
        staking_contract = self.DEDICATED_VAULTS.get(checksum_address)
        
        if not staking_contract:
            print("No staking contract found")
            return {"convex": {}}
        
        print("\nProcessing network: ethereum")
        print("\nProcessing position: USDCfxUSD")
        
        # Combine user's staking contract with common pool info
        vault_info = {
            "staking_contract": staking_contract,
            "name": "USDCfxUSD",
            **self.POOL_INFO
        }
        print(f"\nContract information:")
        print("  staking_contract: " + staking_contract + " (StakingProxyERC20)")
        print("  gauge: " + self.POOL_INFO['gauge'] + " (SharedLiquidityGauge)")
        print("  pool: " + self.POOL_INFO['pool'] + " (CurveStableSwapNG)")
        
        # Initialize contracts
        self.init_contracts(vault_info)
        
        # Get financial data
        result = self._get_financial_data(vault_info)
        
        return result if result else {"convex": {}}
            
    def init_contracts(self, vault_info: Dict[str, str]):
        """
        Initializes Web3 contract instances for user's dedicated vault
        """
        self.staking_contract = self.w3.eth.contract(
            address=vault_info['staking_contract'], 
            abi=self.staking_abi
        )
        self.gauge_contract = self.w3.eth.contract(
            address=self.POOL_INFO['gauge'], 
            abi=self.curve_abi
        )
        self.curve_pool = self.w3.eth.contract(
            address=self.POOL_INFO['pool'], 
            abi=self.curve_abi
        )

    def get_quote_with_fallback(self, token_address: str, amount: int, decimals: int, symbol: str) -> Dict[str, Any]:
        """
        Gets USDC conversion quote for tokens.
        Uses the centralized quote logic from cow_client.py
        """
        print(f"\nAttempting to get quote for {symbol}:")
        
        result = get_quote(
            network="ethereum",
            sell_token=token_address,
            buy_token=self.network_tokens["ethereum"]["USDC"]["address"],
            amount=str(int(amount)),
            token_decimals=decimals,
            token_symbol=symbol
        )

        if result["quote"]:
            return {
                "amount": int(result["quote"]["quote"]["buyAmount"]),
                "decimals": 6,
                "conversion_details": result["conversion_details"]
            }
        
        return {
            "amount": 0,
            "decimals": 6,
            "conversion_details": result["conversion_details"]
        }

    def _calculate_usdc_totals(self, lp_tokens: Dict, rewards: Dict) -> Dict[str, int]:
        """
        Calculate USDC totals for LP tokens and rewards
        """
        # USDC total from LP tokens
        lp_total = 0
        for token_data in lp_tokens.values():
            if "value" in token_data and "USDC" in token_data["value"]:
                lp_total += token_data["value"]["USDC"]["amount"]
        
        # USDC total from rewards
        rewards_total = 0
        for reward_data in rewards.values():
            if "value" in reward_data and "USDC" in reward_data["value"]:
                rewards_total += reward_data["value"]["USDC"]["amount"]
        
        # Combined total
        total = lp_total + rewards_total
        
        return {
            "lp_tokens_total": {
                "wei": lp_total,
                "formatted": f"{lp_total/10**6:.6f}"
            },
            "rewards_total": {
                "wei": rewards_total,
                "formatted": f"{rewards_total/10**6:.6f}"
            },
            "total": {
                "wei": total,
                "formatted": f"{total/10**6:.6f}"
            }
        }

    def _get_financial_data(self, vault_info: Dict[str, str]) -> Dict[str, Any]:
        """
        Fetches and calculates complete position data for user's dedicated vault
        """
        try:
            # Get LP token position size
            print("\nQuerying Curve pool for deposited LP tokens:")
            print(f"  Contract: {self.POOL_INFO['pool']} (CurveStableSwapNG)")
            print("  Function: balanceOf(address) - Returns amount of USDC/fxUSD LP tokens deposited in staking contract")
            contract_lp_balance = self.gauge_contract.functions.balanceOf(
                vault_info['staking_contract']
            ).call()
            
            if contract_lp_balance == 0:
                print("[Convex] No LP balance found")
                return None
            
            print(f"Amount: {contract_lp_balance} (decimals: 18)")
            print(f"Formatted amount: {(Decimal(contract_lp_balance) / Decimal(10**18)):.6f} LP")
            
            # Calculate share of pool
            print("\nQuerying Curve pool contract for total supply:")
            print(f"  Contract: {self.POOL_INFO['pool']}")
            print("  Function: totalSupply() - Returns total USDC/fxUSD LP tokens in Curve pool")
            total_supply = self.curve_pool.functions.totalSupply().call()
            ratio = contract_lp_balance / total_supply if total_supply > 0 else 0
            print(f"\n[Convex] Calculating pool share:")
            print(f"  User LP balance: {contract_lp_balance}")
            print(f"  Total LP supply: {total_supply}")
            print(f"  Share ratio: {ratio:.6%}")

            # Process underlying tokens
            print("\n[Convex] Processing underlying tokens...")
            print("\nQuerying Curve pool contract:")
            print(f"  Contract: {self.POOL_INFO['pool']}")
            print("  Function: N_COINS() - Returns number of tokens in pool")
            n_coins = self.curve_pool.functions.N_COINS().call()
            print(f"Number of tokens in pool: {n_coins}")
            lp_balances = {}
            
            for i in range(n_coins):
                print(f"\nQuerying token information for index {i}:")
                print("  Function: coins(uint256) - Returns token address")
                coin_address = self.curve_pool.functions.coins(i).call()
                if coin_address == "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48":
                    print(f"  Token address: {coin_address} (USDC)")
                elif coin_address == "0x085780639CC2cACd35E474e71f4d000e2405d8f6":
                    print(f"  Token address: {coin_address} (fxUSD)")
                
                print("  Function: balances(uint256) - Returns token balance in pool")
                pool_balance = self.curve_pool.functions.balances(i).call()
                
                token_contract = self.w3.eth.contract(
                    address=coin_address, 
                    abi=self.curve_abi
                )
                print("  Querying token contract:")
                print("    Function: symbol() - Returns token symbol")
                symbol = token_contract.functions.symbol().call()
                print("    Function: decimals() - Returns token decimals")
                decimals = token_contract.functions.decimals().call()
                
                print(f"\nProcessing {symbol}:")
                print(f"  Total in pool: {pool_balance / 10**decimals:.6f} {symbol}")
                
                balance = int(pool_balance * ratio)
                formatted_balance = balance / 10**decimals
                print(f"  User share: {formatted_balance:.6f} {symbol} ({balance} wei)")
                
                token_data = {
                    "amount": balance,
                    "decimals": decimals
                }

                if symbol == "USDC":
                    print("  Converting USDC: Direct 1:1 conversion")
                    token_data["value"] = {
                        "USDC": {
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
                else:
                    print(f"  Converting {symbol}: Using CoWSwap for price discovery")
                    quote_result = self.get_quote_with_fallback(
                        coin_address, balance, decimals, symbol
                    )
                    if quote_result:
                        usdc_value = quote_result["amount"] / 10**6
                        print(f"  → {usdc_value:.6f} USDC")
                        token_data["value"] = {
                            "USDC": quote_result
                        }
                
                lp_balances[symbol] = token_data

            # Process reward tokens
            print("\n[Convex] Processing reward tokens...")
            print("\nQuerying staking contract for earned rewards:")
            print(f"  Contract: {vault_info['staking_contract']}")
            print("  Function: earned() - Returns two arrays:")
            print("    - Array of reward token addresses")
            print("    - Array of unclaimed amounts for each token")
            earned_result = self.staking_contract.functions.earned().call()
            
            print("\nUnclaimed rewards:")
            rewards = {}
            
            # First display all rewards
            for addr, amount in zip(earned_result[0], earned_result[1]):
                token_contract = self.w3.eth.contract(
                    address=addr, 
                    abi=self.curve_abi
                )
                symbol = token_contract.functions.symbol().call()
                decimals = token_contract.functions.decimals().call()
                formatted_amount = amount / 10**decimals
                
                print(f"  • {symbol}:")
                print(f"    Address: {addr}")
                print(f"    Amount: {formatted_amount:.6f} ({amount} wei)")
                print(f"    Decimals: {decimals}")
            
            print("\nConverting rewards to USDC:")
            # Then do the conversions
            for addr, amount in zip(earned_result[0], earned_result[1]):
                token_contract = self.w3.eth.contract(
                    address=addr, 
                    abi=self.curve_abi
                )
                symbol = token_contract.functions.symbol().call()
                decimals = token_contract.functions.decimals().call()
                
                reward_data = {
                    "amount": amount,
                    "decimals": decimals
                }

                if amount > 0:
                    print(f"\nConverting {symbol} rewards to USDC:")
                    quote_result = self.get_quote_with_fallback(
                        addr, amount, decimals, symbol
                    )
                    if quote_result:
                        usdc_value = quote_result["amount"] / 10**6
                        print(f"  → {usdc_value:.6f} USDC")
                        reward_data["value"] = {
                            "USDC": quote_result
                        }
                
                rewards[symbol] = reward_data

            # Calculate totals
            usdc_totals = self._calculate_usdc_totals(lp_balances, rewards)
            total_usdc_value = int(usdc_totals["total"]["wei"])

            print("\n[Convex] Calculation complete")
            
            # Afficher les LP tokens
            for token_symbol, token_data in lp_balances.items():
                if "value" in token_data and "USDC" in token_data["value"]:
                    amount = int(token_data["value"]["USDC"]["amount"])
                    if amount > 0:
                        formatted_amount = amount / 10**6
                        print(f"convex.ethereum.{vault_info['name']}.{token_symbol}: {formatted_amount:.6f} USDC")

            # Afficher les rewards
            for token_symbol, reward_data in rewards.items():
                if "value" in reward_data and "USDC" in reward_data["value"]:
                    amount = int(reward_data["value"]["USDC"]["amount"])
                    if amount > 0:
                        formatted_amount = amount / 10**6
                        print(f"convex.ethereum.{vault_info['name']}.rewards.{token_symbol}: {formatted_amount:.6f} USDC")

            return {
                "convex": {
                    "ethereum": {
                        vault_info['name']: {
                            "staking_contract": vault_info['staking_contract'],
                            "amount": str(contract_lp_balance),
                            "decimals": 18,
                            "lp_tokens": lp_balances,
                            "rewards": rewards
                        },
                        "usdc_totals": usdc_totals
                    },
                    "usdc_totals": {
                        "total": {
                            "wei": total_usdc_value,
                            "formatted": f"{total_usdc_value/10**6:.6f}"
                        }
                    }
                }
            }

        except Exception as e:
            print(f"[Convex] Error: {str(e)}")
            return {"convex": {}}

if __name__ == "__main__":
    from dotenv import load_dotenv
    import os
    
    # Load environment variables
    load_dotenv()
    DEFAULT_USER_ADDRESS = Web3.to_checksum_address(os.getenv('DEFAULT_USER_ADDRESS'))
    
    # Create manager instance
    manager = ConvexBalanceManager()
    
    # Get balances
    balances = manager.get_balances(DEFAULT_USER_ADDRESS)
    
    # Display final result
    print("\n" + "="*80)
    print("FINAL RESULT:")
    print("="*80 + "\n")
    print(json.dumps(balances, indent=2)) 