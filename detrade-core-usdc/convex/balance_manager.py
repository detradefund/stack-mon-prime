from web3 import Web3
import json
from pathlib import Path
from decimal import Decimal
from typing import Dict, Any
import sys

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
        """
        Retrieves all Convex positions and their USDC valuations.
        """
        print("\n=== Processing Convex Protocol positions ===")
        print(f"Checking Convex positions for {address}")
        
        # Check if user has a dedicated vault
        staking_contract = self.DEDICATED_VAULTS.get(address)
        if not staking_contract:
            print("No dedicated Convex vault found for this address")
            return {}
        
        # Combine user's staking contract with common pool info
        vault_info = {
            "staking_contract": staking_contract,
            **self.POOL_INFO
        }
        
        # Initialize contracts
        self.init_contracts(vault_info)
        
        # Get financial data
        result = {}
        financial_data = self._get_financial_data(vault_info)
        
        if financial_data and "convex" in financial_data:
            result = financial_data
            
            # Log positions found
            for network, tokens in result["convex"].items():
                print(f"\n{network.upper()} Network:")
                for token, data in tokens.items():
                    balance_normalized = Decimal(data['amount']) / Decimal(10**data['decimals'])
                    print(f"- {token}:")
                    print(f"  Amount: {balance_normalized:.6f}")
                    
                    # Log underlying tokens
                    print("  Underlying Tokens:")
                    for symbol, token_data in data['lp_tokens'].items():
                        amount = Decimal(token_data['amount']) / Decimal(10**token_data['decimals'])
                        print(f"    - {symbol}: {amount:.6f}")
                        if 'value' in token_data:
                            usdc_value = Decimal(token_data['value']['USDC']['amount']) / Decimal(10**6)
                            print(f"      USDC Value: {usdc_value:.6f}")
                    
                    # Log rewards if any
                    if 'rewards' in data and data['rewards']:
                        print("  Rewards:")
                        for symbol, reward_data in data['rewards'].items():
                            amount = Decimal(reward_data['amount']) / Decimal(10**reward_data['decimals'])
                            print(f"    - {symbol}: {amount:.6f}")
                            if 'value' in reward_data:
                                usdc_value = Decimal(reward_data['value']['USDC']['amount']) / Decimal(10**6)
                                print(f"      USDC Value: {usdc_value:.6f}")
        else:
            print("No positions found")
        
        print("=== Convex Protocol processing complete ===\n")
        return result
            
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
        Gets USDC conversion quote for tokens with fallback mechanism.
        
        For small amounts that can't cover CoW Protocol fees:
        1. Attempts direct quote first
        2. If fails, uses larger amount for price discovery
        3. Applies discovered rate to original amount
        
        Returns quote details including price impact and conversion source
        """
        try:
            # Try direct quote first
            quote = get_quote(
                network="ethereum",
                sell_token=token_address,
                buy_token=self.network_tokens["ethereum"]["USDC"]["address"],
                amount=str(int(amount))
            )
            
            if isinstance(quote, dict) and 'quote' in quote:
                return {
                    "amount": int(quote['quote']['buyAmount']),
                    "decimals": 6,
                    "conversion_details": {
                        "source": "CoWSwap",
                        "price_impact": f"{float(quote['quote'].get('priceImpact', 0))*100:.4f}%",
                        "rate": str(float(quote['quote'].get('sellAmount', 0))/float(quote['quote'].get('buyAmount', 1))),
                        "fee_percentage": f"{float(quote['quote'].get('feeAmount', 0))/float(quote['quote'].get('sellAmount', 1))*100:.4f}%",
                        "fallback": False
                    }
                }
            
            # Fallback silencieusement si le montant est trop petit
            error_response = quote if isinstance(quote, str) else json.dumps(quote)
            if "SellAmountDoesNotCoverFee" in error_response:
                reference_amount = "1000000000000000000000"  # 1000 tokens avec 18 decimals
                fallback_quote = get_quote(
                    network="ethereum",
                    sell_token=token_address,
                    buy_token=self.network_tokens["ethereum"]["USDC"]["address"],
                    amount=reference_amount
                )
                
                if isinstance(fallback_quote, dict) and 'quote' in fallback_quote:
                    # Calculer le rate en utilisant les montants normalisés
                    sell_amount = Decimal(fallback_quote['quote']['sellAmount'])
                    buy_amount = Decimal(fallback_quote['quote']['buyAmount'])
                    
                    # Normaliser les montants (18 decimals -> 1 token, 6 decimals -> 1 USDC)
                    sell_normalized = sell_amount / Decimal(10**18)
                    buy_normalized = buy_amount / Decimal(10**6)
                    
                    # Calculer le rate (USDC par token)
                    rate = buy_normalized / sell_normalized
                    
                    # Appliquer le rate au montant original
                    original_amount_normalized = Decimal(amount) / Decimal(10**18)
                    estimated_value = int(original_amount_normalized * rate * Decimal(10**6))
                    
                    return {
                        "amount": estimated_value,
                        "decimals": 6,
                        "conversion_details": {
                            "source": "CoWSwap-Fallback",
                            "price_impact": "0.0000%",
                            "rate": f"{float(rate):.6f}",  # Format le rate de la même façon que dans les logs
                            "fee_percentage": "N/A",
                            "fallback": True
                        }
                    }
        
        except Exception as e:
            print(f"Error getting quote for {symbol}: {str(e)}")
        
        return None

    def _get_financial_data(self, vault_info: Dict[str, str]) -> Dict[str, Any]:
        """
        Fetches and calculates complete position data for user's dedicated vault
        """
        try:
            # Get LP token position size
            contract_lp_balance = self.gauge_contract.functions.balanceOf(
                vault_info['staking_contract']
            ).call()
            
            if contract_lp_balance == 0:
                return None
                
            # Calculate share of pool
            total_supply = self.gauge_contract.functions.totalSupply().call()
            ratio = contract_lp_balance / total_supply if total_supply > 0 else 0

            # Process underlying tokens
            n_coins = self.curve_pool.functions.N_COINS().call()
            lp_balances = {}
            
            for i in range(n_coins):
                coin_address = self.curve_pool.functions.coins(i).call()
                pool_balance = self.curve_pool.functions.balances(i).call()
                
                token_contract = self.w3.eth.contract(
                    address=coin_address, 
                    abi=self.curve_abi
                )
                symbol = token_contract.functions.symbol().call()
                decimals = token_contract.functions.decimals().call()
                balance = int(pool_balance * ratio)
                
                token_data = {
                    "amount": balance,
                    "decimals": decimals
                }

                # Get USDC value for non-USDC tokens
                if symbol != "USDC":
                    quote_result = self.get_quote_with_fallback(
                        coin_address, balance, decimals, symbol
                    )
                    if quote_result:
                        token_data["value"] = {
                            "USDC": quote_result
                        }
                
                lp_balances[symbol] = token_data

            # Process reward tokens
            earned_result = self.staking_contract.functions.earned().call()
            rewards = {}
            
            for addr, amount in zip(earned_result[0], earned_result[1]):
                if amount == 0:
                    continue
                    
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

                # Get USDC value for reward tokens
                quote_result = self.get_quote_with_fallback(
                    addr, amount, decimals, symbol
                )
                if quote_result:
                    reward_data["value"] = {
                        "USDC": quote_result
                    }
                
                rewards[symbol] = reward_data

            # Structure final response
            return {
                "convex": {
                    "ethereum": {
                        vault_info['name']: {
                            "amount": contract_lp_balance,
                            "decimals": 18,
                            "lp_tokens": lp_balances,
                            "rewards": rewards
                        }
                    }
                }
            }

        except Exception as e:
            print(f"Error in get_financial_data: {e}")
            return None 