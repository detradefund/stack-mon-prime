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
from datetime import datetime
from utils.retry import Web3Retry, APIRetry

# Load environment variables
load_dotenv()

# Web3 configuration with environment variables
ETHEREUM_RPC = os.getenv('ETHEREUM_RPC')

# Zero address for API calls
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

# Production addresses
PRODUCTION_ADDRESS = Web3.to_checksum_address("0xc6835323372A4393B90bCc227c58e82D45CE4b7d")

# Contract addresses
PENDLE_BOOSTER_ADDRESS = '0x4D32C8Ff2fACC771eC7Efc70d6A8468bC30C26bF'

# Pool configurations
POOL_CONFIGS = {
    'ethereum': {
        'GHO-USR': {
            'market_address': '0x82D810ededb09614144900F914e75Dd76700f19d',
            'reward_pool_address': '0xC565b6781e629f29600741543c2403dbD49391F2',
            'booster_address': PENDLE_BOOSTER_ADDRESS,
            'decimals': 18
        },
        'fGHO': {
            'market_address': '0xC64D59eb11c869012C686349d24e1D7C91C86ee2',
            'reward_pool_address': "0xba0928d9d0C2dA79522E45244CE859838999b21c",
            'booster_address': PENDLE_BOOSTER_ADDRESS,
            'decimals': 18
        }
    }
}

# Get token addresses from network config
PENDLE_TOKEN_ADDRESS = NETWORK_TOKENS['ethereum']['PENDLE']['address']
CRV_TOKEN_ADDRESS = NETWORK_TOKENS['ethereum']['CRV']['address']
USDC_ADDRESS = NETWORK_TOKENS['ethereum']['USDC']['address']

# Pendle API configuration
PENDLE_API_BASE = "https://api-v2.pendle.finance/core/v1/sdk/1/markets"

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
    },
    {
        "constant": True,
        "inputs": [],
        "name": "getRewardTokens",
        "outputs": [{"name": "", "type": "address[]"}],
        "payable": False,
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
        
        # Initialize contracts and pool info for each network and pool
        self.pools = {}
        for network, pools in POOL_CONFIGS.items():
            self.pools[network] = {}
            for pool_id, config in pools.items():
                self.pools[network][pool_id] = {
                    'config': config,
                    'reward_pool': self.w3.eth.contract(
                        address=self.w3.to_checksum_address(config['reward_pool_address']),
                        abi=BASE_REWARD_POOL_ABI
                    ),
                    'pendle_booster': self.w3.eth.contract(
                        address=self.w3.to_checksum_address(config['booster_address']),
                        abi=PENDLE_BOOSTER_ABI
                    )
                }
                
                # Get pool info and reward tokens
                pool_info = self.get_pool_info(network, pool_id)
                if pool_info:
                    self.pools[network][pool_id]['pool_info'] = pool_info
                    # Get reward tokens dynamically
                    reward_tokens = self.get_reward_tokens(network, pool_id)
                    if reward_tokens:
                        self.pools[network][pool_id]['reward_tokens'] = reward_tokens

        self.current_timestamp = int(datetime.now().timestamp())

    def get_pool_info(self, network, pool_id):
        """
        Get pool information from PendleBoosterMainchain contract
        Returns tuple of (market, token, rewardPool, shutdown)
        """
        try:
            pool = self.pools[network][pool_id]
            pool_info = Web3Retry.call_contract_function(
                pool['pendle_booster'].functions.poolInfo(pool['reward_pool'].functions.pid().call()).call
            )
            return {
                'market': pool_info[0],
                'token': pool_info[1],
                'rewardPool': pool_info[2],
                'shutdown': pool_info[3]
            }
        except Exception as e:
            print(f"Error fetching pool info for {network}.{pool_id}: {e}")
            return None

    def get_reward_tokens(self, network, pool_id):
        """
        Get the list of reward tokens from the reward pool contract
        Returns a list of token addresses
        """
        try:
            pool = self.pools[network][pool_id]
            reward_tokens = Web3Retry.call_contract_function(
                pool['reward_pool'].functions.getRewardTokens().call
            )
            return reward_tokens
        except Exception as e:
            print(f"Error fetching reward tokens for {network}.{pool_id}: {e}")
            return []

    def get_staked_balance(self, network, pool_id, address=None):
        """
        Get staked LP balance for a specific pool
        If no address is provided, uses production address
        Returns the raw balance in wei
        """
        if address is None:
            address = PRODUCTION_ADDRESS

        try:
            pool = self.pools[network][pool_id]
            balance = Web3Retry.call_contract_function(
                pool['reward_pool'].functions.balanceOf(
                    self.w3.to_checksum_address(address)
                ).call
            )
            return balance
        except Exception as e:
            print(f"Error while fetching balance for {network}.{pool_id}: {e}")
            return 0

    def is_pt_expired(self, token_data: Dict) -> bool:
        """
        Check if a PT token is expired
        """
        expiry = token_data.get('expiry')
        if not expiry:
            return False
        return self.current_timestamp > expiry

    def get_remove_liquidity_data(self, network, pool_id, balance_wei):
        """
        Get remove liquidity data from Pendle API including amount out and price impact
        Returns a tuple of (amount_out, price_impact)
        """
        try:
            pool = self.pools[network][pool_id]
            url = f"{PENDLE_API_BASE}/{pool['config']['market_address']}/remove-liquidity"
            
            # Validate and format parameters
            if not isinstance(balance_wei, (int, str)):
                raise ValueError(f"Invalid balance_wei type: {type(balance_wei)}")
            
            balance_str = str(balance_wei)
            if not balance_str.isdigit():
                raise ValueError(f"Invalid balance_wei value: {balance_str}")
            
            # Format parameters to match browser request
            params = {
                "receiver": self.w3.to_checksum_address(PRODUCTION_ADDRESS),
                "slippage": "0.01",
                "enableAggregator": "true",
                "amountIn": balance_str,
                "tokenOut": USDC_ADDRESS
            }
            
            # Add headers to match browser request
            headers = {
                "accept": "application/json"
            }
            
            print(f"\nMaking Pendle API request:")
            print(f"URL: {url}")
            print(f"Headers: {json.dumps(headers, indent=2)}")
            print(f"Params: {json.dumps(params, indent=2)}")
            
            try:
                response = APIRetry.get(url, params=params, headers=headers)
                response.raise_for_status()
                
                data = response.json()['data']
                amount_out = int(data['amountOut'])
                price_impact = float(data['priceImpact'])
                
                return amount_out, price_impact
            except requests.exceptions.RequestException as e:
                print(f"Error fetching remove liquidity data: {e}")
                if hasattr(e, 'response') and e.response is not None:
                    print(f"Response status: {e.response.status_code}")
                    print(f"Response headers: {json.dumps(dict(e.response.headers), indent=2)}")
                    print(f"Response body: {e.response.text}")
                return 0, 0
            
        except Exception as e:
            print(f"Error fetching remove liquidity data: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response status: {e.response.status_code}")
                print(f"Response body: {e.response.text}")
            return 0, 0

    def get_earned_rewards(self, network, pool_id, address=None):
        """
        Get earned rewards for a specific pool
        If no address is provided, uses production address
        Returns a dict with raw reward amounts in wei
        """
        if address is None:
            address = PRODUCTION_ADDRESS

        rewards = {}
        try:
            pool = self.pools[network][pool_id]
            reward_tokens = pool.get('reward_tokens', [])
            
            for token_address in reward_tokens:
                earned = Web3Retry.call_contract_function(
                    pool['reward_pool'].functions.earned(
                        self.w3.to_checksum_address(address),
                        self.w3.to_checksum_address(token_address)
                    ).call
                )
                # Get token symbol from address
                token_symbol = self.get_token_symbol(network, token_address)
                if token_symbol:
                    rewards[token_symbol] = earned

            return rewards
        except Exception as e:
            print(f"Error fetching earned rewards for {network}.{pool_id}: {e}")
            return {}

    def get_token_symbol(self, network, token_address):
        """
        Get token symbol from address using NETWORK_TOKENS
        """
        for symbol, token_info in NETWORK_TOKENS[network].items():
            if token_info['address'].lower() == token_address.lower():
                return symbol
        return None

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
            
            # Handle case where price_impact is "N/A" (fallback case)
            if price_impact_str == "N/A":
                price_impact = 0
            else:
                price_impact = float(price_impact_str.rstrip("%"))
            
            return buy_amount, price_impact/100, True, result["conversion_details"]

        return 0, 0, False, {}

    def get_balances(self, address: str) -> Dict[str, Any]:
        print("\n" + "="*80)
        print("EQUILIBRIA BALANCE MANAGER")
        print("="*80)
        
        checksum_address = Web3.to_checksum_address(address)
        result = {"equilibria": {}}
        
        try:
            protocol_total = 0
            
            for network, pools in self.pools.items():
                print(f"\nProcessing network: {network}")
                result["equilibria"][network] = {}
                network_total = 0
                
                for pool_id, pool in pools.items():
                    print(f"\nProcessing position: {pool_id}")
                    
                    # Get staked balance
                    balance = self.get_staked_balance(network, pool_id, address)
                    if balance == 0:
                        continue
                    
                    # Get rewards
                    rewards = self.get_earned_rewards(network, pool_id, address)
                    
                    # Get LP value in USDC
                    usdc_amount, price_impact = self.get_remove_liquidity_data(network, pool_id, balance)
                    
                    # Calculate rewards value in USDC
                    rewards_total = 0
                    rewards_data = {}
                    for token, amount in rewards.items():
                        if amount > 0:
                            token_usdc_amount, token_price_impact, success, conversion_details = self.get_reward_value_in_usdc(
                                token, str(amount)
                            )
                            rewards_total += token_usdc_amount
                            rewards_data[token] = {
                                "amount": str(amount),
                                "decimals": pool['config']['decimals'],
                                "value": {
                                    "USDC": {
                                        "amount": token_usdc_amount,
                                        "decimals": 6,
                                        "conversion_details": conversion_details
                                    }
                                }
                            }
                    
                    # Calculate position total
                    position_total = usdc_amount + rewards_total
                    network_total += position_total
                    
                    # Add position data to result
                    result["equilibria"][network][pool_id] = {
                        "staking_contract": pool['pool_info']['rewardPool'],
                        "amount": str(balance),
                        "decimals": pool['config']['decimals'],
                        "value": {
                            "USDC": {
                                "amount": usdc_amount,
                                "decimals": 6,
                                "conversion_details": {
                                    "source": "Pendle SDK",
                                    "price_impact": f"{price_impact:.6f}",
                                    "rate": f"{Decimal(usdc_amount)/Decimal(balance)*Decimal(10**12):.6f}",
                                    "fee_percentage": "0.0000%",
                                    "fallback": False,
                                    "note": "Direct Conversion using Pendle SDK"
                                }
                            }
                        },
                        "rewards": rewards_data,
                        "totals": {
                            "wei": position_total,
                            "formatted": f"{position_total/1e6:.6f}"
                        }
                    }
                
                # Add network totals
                result["equilibria"][network]["totals"] = {
                    "wei": network_total,
                    "formatted": f"{network_total/1e6:.6f}"
                }
                
                protocol_total += network_total
            
            # Add protocol totals
            result["equilibria"]["totals"] = {
                "wei": protocol_total,
                "formatted": f"{protocol_total/1e6:.6f}"
            }
            
        except Exception as e:
            print(f"✗ Error fetching Equilibria positions: {str(e)}")
            return {"equilibria": {
                "totals": {
                    "wei": 0,
                    "formatted": "0.000000"
                }
            }}
        
        return result

# Code for direct testing
if __name__ == "__main__":
    import sys
    
    # Use command line argument if provided, otherwise use PRODUCTION_ADDRESS
    test_address = sys.argv[1] if len(sys.argv) > 1 else PRODUCTION_ADDRESS
    
    bm = BalanceManager()
    results = bm.get_balances(test_address)
    
    # Display position summary
    if results and "equilibria" in results:
        data = results["equilibria"]
        for network, pools in data.items():
            if "ethereum" in pools:
                for pool_id, pool in pools["ethereum"].items():
                    if "value" in pool and "USDC" in pool["value"]:
                        print(f"equilibria.{network}.{pool_id}: {pool['value']['USDC']['amount']/1e6:.6f} USDC")
                    if "rewards" in pool:
                        for token, reward in pool["rewards"].items():
                            if "value" in reward and "USDC" in reward["value"]:
                                print(f"equilibria.{network}.{pool_id}.rewards.{token}: {reward['value']['USDC']['amount']/1e6:.6f} USDC")
    
    print("\n" + "="*80)
    print("FINAL RESULT:")
    print("="*80 + "\n")
    print(json.dumps(results, indent=2))
