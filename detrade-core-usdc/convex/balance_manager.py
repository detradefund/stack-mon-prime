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
        """
        Retrieves all Convex positions and their USDC valuations.
        """
        print("\n" + "="*80)
        print("CONVEX BALANCE MANAGER")
        print("="*80)
        
        print("\nDebug get_balances:")
        print(f"Processing address: {address}")
        
        # Convertir l'adresse en format checksum
        checksum_address = Web3.to_checksum_address(address)
        print(f"Checksum address: {checksum_address}")
        
        # Check if user has a dedicated vault
        staking_contract = self.DEDICATED_VAULTS.get(checksum_address)
        print(f"Staking contract for {checksum_address}: {staking_contract}")
        
        if not staking_contract:
            print("No staking contract found")
            return {}
        
        # Combine user's staking contract with common pool info
        vault_info = {
            "staking_contract": staking_contract,
            "name": "USDCfxUSD",
            **self.POOL_INFO
        }
        print(f"Vault info: {json.dumps(vault_info, indent=2)}")
        
        # Initialize contracts
        self.init_contracts(vault_info)
        print("Contracts initialized")
        
        # Get financial data
        result = {}
        financial_data = self._get_financial_data(vault_info)
        
        if financial_data and "convex" in financial_data:
            result = financial_data
        
        if result and "convex" in result:
            total_value = sum(
                float(pool_data['usdc_totals']['total']['formatted'])
                for chain_data in result['convex'].values()
                for pool_data in chain_data.values()
                if isinstance(pool_data, dict) and 'usdc_totals' in pool_data
            )
            print("\n" + "="*80)
            print(f"TOTAL CONVEX VALUE: {total_value:.6f} USDC")
            print("="*80)
        
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
        Includes retry mechanism for technical errors.
        """
        retry_delays = [1, 3, 3]  # Délais en secondes entre les tentatives
        
        print(f"\nAttempting to get quote for {symbol}:")
        
        for attempt, delay in enumerate(retry_delays, 1):
            try:
                print(f"[Attempt {attempt}/3] Requesting CoWSwap quote...")
                
                # Try direct quote first
                quote = get_quote(
                    network="ethereum",
                    sell_token=token_address,
                    buy_token=self.network_tokens["ethereum"]["USDC"]["address"],
                    amount=str(int(amount))
                )
                
                if isinstance(quote, dict) and 'quote' in quote:
                    # Calculer le rate correctement (USDC par token)
                    sell_amount = Decimal(quote['quote']['sellAmount']) / Decimal(10**decimals)
                    buy_amount = Decimal(quote['quote']['buyAmount']) / Decimal(10**6)
                    rate = buy_amount / sell_amount if sell_amount else Decimal('0')
                    
                    print(f"✓ Direct quote successful:")
                    print(f"  - Sell amount: {sell_amount} {symbol}")
                    print(f"  - Buy amount: {buy_amount} USDC")
                    print(f"  - Rate: {float(rate):.6f} USDC/{symbol}")
                    print(f"  - Fee: {float(quote['quote'].get('feeAmount', 0))/float(quote['quote'].get('sellAmount', 1))*100:.4f}%")
                    
                    return {
                        "amount": int(quote['quote']['buyAmount']),
                        "decimals": 6,
                        "conversion_details": {
                            "source": "CoWSwap",
                            "price_impact": f"{float(quote['quote'].get('priceImpact', 0))*100:.4f}%",
                            "rate": f"{float(rate):.6f}",
                            "fee_percentage": f"{float(quote['quote'].get('feeAmount', 0))/float(quote['quote'].get('sellAmount', 1))*100:.4f}%",
                            "fallback": False,
                            "note": "Direct CoWSwap quote"
                        }
                    }
                
                # Gestion des erreurs CoWSwap
                error_response = quote if isinstance(quote, str) else json.dumps(quote)
                
                # Cas spécifique: montant trop petit
                if "SellAmountDoesNotCoverFee" in error_response:
                    print("! Amount too small for direct quote, trying fallback method...")
                    reference_amount = "1000000000000000000000"  # 1000 tokens
                    
                    print(f"Requesting quote with reference amount (1000 {symbol})...")
                    fallback_quote = get_quote(
                        network="ethereum",
                        sell_token=token_address,
                        buy_token=self.network_tokens["ethereum"]["USDC"]["address"],
                        amount=reference_amount
                    )
                    
                    if isinstance(fallback_quote, dict) and 'quote' in fallback_quote:
                        # Calculer le rate en utilisant les montants normalisés
                        sell_amount = Decimal(fallback_quote['quote']['sellAmount']) / Decimal(10**decimals)
                        buy_amount = Decimal(fallback_quote['quote']['buyAmount']) / Decimal(10**6)
                        rate = buy_amount / sell_amount if sell_amount else Decimal('0')
                        
                        # Appliquer le rate au montant original
                        original_amount_normalized = Decimal(amount) / Decimal(10**decimals)
                        estimated_value = int(original_amount_normalized * rate * Decimal(10**6))
                        
                        print(f"✓ Fallback successful:")
                        print(f"  - Discovered rate: {float(rate):.6f} USDC/{symbol}")
                        print(f"  - Estimated value: {estimated_value/10**6:.6f} USDC")
                        
                        return {
                            "amount": estimated_value,
                            "decimals": 6,
                            "conversion_details": {
                                "source": "CoWSwap-Fallback",
                                "price_impact": "0.0000%",
                                "rate": f"{float(rate):.6f}",
                                "fee_percentage": "N/A",
                                "fallback": True,
                                "note": "Using reference amount of 1000 tokens for price discovery due to small amount"
                            }
                        }
                    
                    print("✗ Fallback method failed")
                
                # Autres cas d'erreur CoWSwap
                print(f"✗ CoWSwap error: {error_response[:200]}...")
                error_details = {
                    "amount": 0,
                    "decimals": 6,
                    "conversion_details": {
                        "source": "Error",
                        "price_impact": "0.0000%",
                        "rate": "0.000000",
                        "fee_percentage": "0.0000%",
                        "fallback": False,
                        "note": f"CoWSwap error: {error_response[:200]}..."
                    }
                }
                return error_details

            except Exception as e:
                print(f"✗ Technical error (attempt {attempt}/3):")
                print(f"  {str(e)}")
                
                if attempt < len(retry_delays):
                    print(f"  Retrying in {delay} seconds...")
                    time.sleep(delay)
                    continue
                
                print("✗ All retry attempts failed")
                return {
                    "amount": 0,
                    "decimals": 6,
                    "conversion_details": {
                        "source": "Error",
                        "price_impact": "0.0000%",
                        "rate": "0.000000",
                        "fee_percentage": "0.0000%",
                        "fallback": False,
                        "note": f"Technical error after 3 retries: {str(e)[:200]}..."
                    }
                }

    def _calculate_usdc_totals(self, lp_tokens: Dict, rewards: Dict) -> Dict[str, int]:
        """
        Calcule les totaux USDC pour les LP tokens et les rewards
        """
        # Total USDC des LP tokens
        lp_total = 0
        for token_data in lp_tokens.values():
            if "value" in token_data and "USDC" in token_data["value"]:
                lp_total += token_data["value"]["USDC"]["amount"]
        
        # Total USDC des rewards
        rewards_total = 0
        for reward_data in rewards.values():
            if "value" in reward_data and "USDC" in reward_data["value"]:
                rewards_total += reward_data["value"]["USDC"]["amount"]
        
        # Total combiné
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
            print("\n[Convex] Fetching position data...")
            
            # Get LP token position size
            contract_lp_balance = self.gauge_contract.functions.balanceOf(
                vault_info['staking_contract']
            ).call()
            
            if contract_lp_balance == 0:
                print("[Convex] No LP balance found")
                return None
            
            print(f"Amount: {contract_lp_balance} (decimals: 18)")
            print(f"Formatted amount: {(Decimal(contract_lp_balance) / Decimal(10**18)):.6f} LP")
            
            # Calculate share of pool
            total_supply = self.gauge_contract.functions.totalSupply().call()
            ratio = contract_lp_balance / total_supply if total_supply > 0 else 0

            # Process underlying tokens
            print("[Convex] Processing underlying tokens...")
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

                # Pour USDC, ajoutons la valeur avec une explication
                if symbol == "USDC":
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
                else:  # Pour fxUSD et autres tokens non-USDC
                    quote_result = self.get_quote_with_fallback(
                        coin_address, balance, decimals, symbol
                    )
                    if quote_result:
                        token_data["value"] = {
                            "USDC": quote_result
                        }
                
                lp_balances[symbol] = token_data

            # Process reward tokens
            print("[Convex] Processing reward tokens...")
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

            # Calculer les totaux avant de retourner
            usdc_totals = self._calculate_usdc_totals(lp_balances, rewards)

            print("[Convex] Calculation complete")
            return {
                "convex": {
                    "ethereum": {
                        vault_info['name']: {
                            "staking_contract": vault_info['staking_contract'],
                            "amount": contract_lp_balance,
                            "decimals": 18,
                            "lp_tokens": lp_balances,
                            "rewards": rewards,
                            "usdc_totals": usdc_totals
                        }
                    }
                }
            }

        except Exception as e:
            print(f"[Convex] Error: {str(e)}")
            return None 

if __name__ == "__main__":
    from dotenv import load_dotenv
    import os
    
    # Charger les variables d'environnement
    load_dotenv()
    DEFAULT_USER_ADDRESS = Web3.to_checksum_address(os.getenv('DEFAULT_USER_ADDRESS'))
    
    # Créer une instance du manager
    manager = ConvexBalanceManager()
    
    # Récupérer les balances
    balances = manager.get_balances(DEFAULT_USER_ADDRESS)
    
    # Afficher le résultat final
    print("\n" + "="*80)
    print("FINAL RESULT:")
    print("="*80 + "\n")
    print(json.dumps(balances, indent=2)) 