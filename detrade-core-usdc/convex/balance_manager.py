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
        
        print("\nDebug get_balances:")
        print(f"Processing address: {address}")
        checksum_address = Web3.to_checksum_address(address)
        print(f"Checksum address: {checksum_address}")
        
        # Check if user has a dedicated vault
        staking_contract = self.DEDICATED_VAULTS.get(checksum_address)
        print(f"Staking contract for {checksum_address}: {staking_contract}")
        
        if not staking_contract:
            print("No staking contract found")
            return {"convex": {}}
        
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

            # Calculer les totaux
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