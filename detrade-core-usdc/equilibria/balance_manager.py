from web3 import Web3
import os
from dotenv import load_dotenv
import requests
from config.networks import NETWORK_TOKENS
from cowswap.cow_client import get_quote
import time
from decimal import Decimal
import json
from typing import Dict, Any

# Load environment variables
load_dotenv()

# Web3 configuration with environment variables
ETHEREUM_RPC = os.getenv('ETHEREUM_RPC')
DEFAULT_USER_ADDRESS = os.getenv('DEFAULT_USER_ADDRESS')

# Contract addresses
BASE_REWARD_POOL_ADDRESS = '0xC565b6781e629f29600741543c2403dbD49391F2'
PENDLE_BOOSTER_ADDRESS = '0x4D32C8Ff2fACC771eC7Efc70d6A8468bC30C26bF'

# Get token addresses from network config
PENDLE_TOKEN_ADDRESS = NETWORK_TOKENS['ethereum']['PENDLE']['address']
CRV_TOKEN_ADDRESS = NETWORK_TOKENS['ethereum']['CRV']['address']
USDC_ADDRESS = NETWORK_TOKENS['ethereum']['USDC']['address']

# Pendle API configuration
PENDLE_API_BASE = "https://api-v2.pendle.finance/core/v1/sdk/1/markets"
MARKET_ADDRESS = "0x82D810ededb09614144900F914e75Dd76700f19d"

# BaseRewardPoolV2 ABI
BASE_REWARD_POOL_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "pid",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "address", "name": "_account", "type": "address"},
            {"internalType": "address", "name": "_rewardToken", "type": "address"}
        ],
        "name": "earned",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# PendleBoosterMainchain ABI
PENDLE_BOOSTER_ABI = [
    {
        "name": "poolInfo",
        "inputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "outputs": [
            {"internalType": "address", "name": "market", "type": "address"},
            {"internalType": "address", "name": "token", "type": "address"},
            {"internalType": "address", "name": "rewardPool", "type": "address"},
            {"internalType": "bool", "name": "shutdown", "type": "bool"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

class BalanceManager:
    def __init__(self):
        if not ETHEREUM_RPC:
            raise ValueError("ETHEREUM_RPC not configured in .env file")
        self.w3 = Web3(Web3.HTTPProvider(ETHEREUM_RPC))
        
        # Initialize contracts
        self.reward_pool = self.w3.eth.contract(
            address=self.w3.to_checksum_address(BASE_REWARD_POOL_ADDRESS),
            abi=BASE_REWARD_POOL_ABI
        )
        self.pendle_booster = self.w3.eth.contract(
            address=self.w3.to_checksum_address(PENDLE_BOOSTER_ADDRESS),
            abi=PENDLE_BOOSTER_ABI
        )
        
        # Get pid on initialization as it won't change
        self.pool_id = self.get_pool_id()
        
        # Get pool info using pid
        self.pool_info = self.get_pool_info(self.pool_id)

    def get_pool_id(self):
        """
        Get the pool ID from the BaseRewardPoolV2 contract
        """
        try:
            pid = self.reward_pool.functions.pid().call()
            return pid
        except Exception as e:
            print(f"Error fetching pool ID: {e}")
            return None

    def get_pool_info(self, pool_id):
        """
        Get pool information from PendleBoosterMainchain contract
        Returns tuple of (market, token, rewardPool, shutdown)
        """
        try:
            pool_info = self.pendle_booster.functions.poolInfo(pool_id).call()
            return {
                'market': pool_info[0],
                'token': pool_info[1],
                'rewardPool': pool_info[2],
                'shutdown': pool_info[3]
            }
        except Exception as e:
            print(f"Error fetching pool info: {e}")
            return None

    def get_staked_balance(self, address=None):
        """
        Get staked LP-GHO-USR balance from BaseRewardPoolV2
        If no address is provided, uses default address
        Returns the raw balance in wei
        """
        if address is None:
            if not DEFAULT_USER_ADDRESS:
                raise ValueError("DEFAULT_USER_ADDRESS not configured in .env file")
            address = DEFAULT_USER_ADDRESS

        try:
            balance = self.reward_pool.functions.balanceOf(
                self.w3.to_checksum_address(address)
            ).call()
            return balance
        except Exception as e:
            print(f"Error while fetching balance: {e}")
            return 0

    def get_remove_liquidity_data(self, balance_wei):
        """
        Get remove liquidity data from Pendle API including amount out and price impact
        Returns a tuple of (amount_out, price_impact)
        """
        try:
            url = f"{PENDLE_API_BASE}/{MARKET_ADDRESS}/remove-liquidity"
            params = {
                "receiver": DEFAULT_USER_ADDRESS,
                "slippage": "0.01",
                "enableAggregator": "true",
                "amountIn": str(balance_wei),
                "tokenOut": USDC_ADDRESS
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()['data']
            amount_out = int(data['amountOut'])  # Raw amount in USDC wei
            price_impact = float(data['priceImpact'])
            
            return amount_out, price_impact
            
        except Exception as e:
            print(f"Error fetching remove liquidity data: {e}")
            return 0, 0

    def get_earned_rewards(self, address=None):
        """
        Get earned rewards (PENDLE and CRV) for an address
        If no address is provided, uses default address
        Returns a dict with raw reward amounts in wei
        """
        if address is None:
            if not DEFAULT_USER_ADDRESS:
                raise ValueError("DEFAULT_USER_ADDRESS not configured in .env file")
            address = DEFAULT_USER_ADDRESS

        rewards = {}
        try:
            # Get PENDLE rewards
            pendle_earned = self.reward_pool.functions.earned(
                self.w3.to_checksum_address(address),
                self.w3.to_checksum_address(PENDLE_TOKEN_ADDRESS)
            ).call()
            rewards['PENDLE'] = pendle_earned

            # Get CRV rewards
            crv_earned = self.reward_pool.functions.earned(
                self.w3.to_checksum_address(address),
                self.w3.to_checksum_address(CRV_TOKEN_ADDRESS)
            ).call()
            rewards['CRV'] = crv_earned

            return rewards
        except Exception as e:
            print(f"Error fetching earned rewards: {e}")
            return {'PENDLE': 0, 'CRV': 0}

    def get_default_address_balance(self):
        """
        Get staked LP-GHO-USR balance for default address
        """
        return self.get_staked_balance()

    def get_lp_token_rate(self):
        """
        Calculate the rate of 1 LP token in USDC
        Returns a tuple of (rate, price_impact)
        """
        try:
            # Use 1 LP token as reference amount
            one_token = self.w3.to_wei('1', 'ether')  # 1e18 wei
            
            url = f"{PENDLE_API_BASE}/{MARKET_ADDRESS}/remove-liquidity"
            params = {
                "receiver": DEFAULT_USER_ADDRESS,
                "slippage": "0.01",
                "enableAggregator": "true",
                "amountIn": str(one_token),
                "tokenOut": USDC_ADDRESS
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()['data']
            amount_out = int(data['amountOut'])
            price_impact = float(data['priceImpact'])
            
            # Calculate rate (USDC per LP token)
            rate = amount_out / 1e6  # Convert USDC wei to USDC
            
            return rate, price_impact
        except Exception as e:
            print(f"Error calculating LP token rate: {e}")
            return 0, 0

    def get_reward_value_in_usdc(self, token_symbol: str, amount: str) -> tuple:
        """
        Get USDC value for reward tokens using CoW Swap
        Returns tuple of (amount_out, price_impact, success, conversion_details)
        """
        print(f"\nAttempting to get quote for {token_symbol}:")
        
        result = get_quote(
            network="ethereum",
            sell_token=NETWORK_TOKENS['ethereum'][token_symbol]['address'],
            buy_token=USDC_ADDRESS,
            amount=amount,
            token_decimals=NETWORK_TOKENS['ethereum'][token_symbol]['decimals'],
            token_symbol=token_symbol
        )

        if result["quote"]:
            buy_amount = int(result["quote"]["quote"]["buyAmount"])
            price_impact_str = result["conversion_details"].get("price_impact", "0")
            
            # Gérer le cas où price_impact est "N/A" (cas du fallback)
            if price_impact_str == "N/A":
                price_impact = 0
            else:
                price_impact = float(price_impact_str.rstrip("%"))
            
            return buy_amount, price_impact/100, True, result["conversion_details"]

        return 0, 0, False, {}

    def get_balances(self, address: str) -> Dict[str, Any]:
        """
        Get all balances for a given address
        """
        if address is None:
            if not DEFAULT_USER_ADDRESS:
                raise ValueError("DEFAULT_USER_ADDRESS not configured in .env file")
            address = DEFAULT_USER_ADDRESS

        print("\n" + "="*80)
        print("EQUILIBRIA BALANCE MANAGER")
        print("="*80)

        print("\nDebug get_balances:")
        print(f"Processing address: {address}")
        print(f"Checksum address: {Web3.to_checksum_address(address)}")

        result = {"equilibria": {}}
        total_usdc_wei = 0

        print("\nProcessing network: ethereum")
        print("\nProcessing token: GHO-USR LP")
        
        # Afficher vault info avec une meilleure structure
        print("\nVault info:")
        print("  staking_contract: " + BASE_REWARD_POOL_ADDRESS)
        print("  name: GHO-USR")
        print("  market: " + MARKET_ADDRESS)
        print("  booster: " + PENDLE_BOOSTER_ADDRESS)

        balance_wei = self.get_staked_balance(address)
        print(f"\nAmount: {balance_wei} (decimals: 18)")
        print(f"Formatted amount: {balance_wei / 1e18:.6f} GHO-USR LP")

        print("\nAttempting to get quote for GHO-USR LP:")
        print("[Attempt 1/1] Requesting Pendle SDK quote...")
        
        amount_out, price_impact = self.get_remove_liquidity_data(balance_wei)
        rate, rate_impact = self.get_lp_token_rate()

        print("✓ Quote successful:")
        print(f"  - Sell amount: {balance_wei / 1e18:.6f} GHO-USR LP")
        print(f"  - Buy amount: {amount_out / 1e6:.6f} USDC")
        print(f"  - Rate: {rate:.6f} USDC/GHO-USR LP")
        print(f"  - Price impact: {price_impact * 100:.4f}%")

        earned_rewards = self.get_earned_rewards(address)
        rewards_total_usdc = 0
        rewards_dict = {}

        # Process rewards
        for token, amount in earned_rewards.items():
            if int(amount) > 0:
                print(f"\nProcessing reward token: {token}")
                print(f"Amount: {amount} (decimals: 18)")
                print(f"Formatted amount: {int(amount) / 1e18:.6f} {token}")
                
                usdc_amount, price_impact, success, conversion_details = self.get_reward_value_in_usdc(token, str(amount))
                if success:
                    rewards_total_usdc += usdc_amount
                    rewards_dict[token] = {
                        "amount": str(amount),
                        "decimals": 18,
                        "value": {
                            "USDC": {
                                "amount": usdc_amount,
                                "decimals": 6,
                                "conversion_details": conversion_details
                            }
                        }
                    }
                else:
                    print("✗ Quote failed")

        total_usdc = amount_out + rewards_total_usdc
        total_usdc_wei = total_usdc  # Pour le total global

        # Construction du dictionnaire de résultat
        result["equilibria"]["ethereum"] = {
            "GHO-USR": {
                "staking_contract": self.pool_info['rewardPool'],
                "amount": str(balance_wei),
                "decimals": 18,
                "value": {
                    "USDC": {
                        "amount": amount_out,
                        "decimals": 6,
                        "conversion_details": {
                            "source": "Pendle SDK",
                            "price_impact": f"{price_impact * 100:.4f}%",
                            "rate": f"{rate:.6f}",
                            "fee_percentage": "0.0000%",
                            "fallback": False,
                            "note": "Direct Conversion using Pendle SDK"
                        }
                    }
                },
                "rewards": rewards_dict
            },
            "usdc_totals": {
                "lp_tokens_total": {
                    "wei": amount_out,
                    "formatted": f"{amount_out / 1e6:.6f}"
                },
                "rewards_total": {
                    "wei": rewards_total_usdc,
                    "formatted": f"{rewards_total_usdc / 1e6:.6f}"
                },
                "total": {
                    "wei": total_usdc,
                    "formatted": f"{total_usdc / 1e6:.6f}"
                }
            }
        }

        # Ajouter le total global au niveau du protocole
        result["equilibria"]["usdc_totals"] = {
            "total": {
                "wei": total_usdc_wei,
                "formatted": f"{total_usdc_wei / 1e6:.6f}"
            }
        }

        # Déplacer l'affichage des positions ici, après tous les calculs
        print("\n[Equilibria] Calculation complete")
        
        # Afficher le LP token
        if amount_out > 0:
            print(f"equilibria.ethereum.GHO-USR: {amount_out/1e6:.6f} USDC")
        
        # Afficher les rewards
        if rewards_total_usdc > 0:
            print(f"equilibria.ethereum.GHO-USR.rewards.PENDLE: {rewards_total_usdc/1e6:.6f} USDC")

        return result

# Code for direct testing
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    import sys
    
    # Get address from command line or .env
    test_address = sys.argv[1] if len(sys.argv) > 1 else os.getenv('DEFAULT_USER_ADDRESS')
    
    if not test_address:
        print("Error: No address provided and DEFAULT_USER_ADDRESS not found in .env")
        sys.exit(1)
        
    bm = BalanceManager()
    results = bm.get_balances(test_address)
    print(json.dumps(results, indent=2))
