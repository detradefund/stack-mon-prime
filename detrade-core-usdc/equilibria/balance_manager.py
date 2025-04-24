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

        self.current_timestamp = int(datetime.now().timestamp())

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

    def is_pt_expired(self, token_data: Dict) -> bool:
        """
        Check if a PT token is expired
        """
        expiry = token_data.get('expiry')
        if not expiry:
            return False
        return self.current_timestamp > expiry

    def get_remove_liquidity_data(self, balance_wei):
        """
        Get remove liquidity data from Pendle API including amount out and price impact
        Returns a tuple of (amount_out, price_impact)
        """
        try:
            # Check if token is expired
            token_data = NETWORK_TOKENS['ethereum'].get('GHO-USR')
            if token_data and token_data.get('protocol') == 'pendle' and self.is_pt_expired(token_data):
                print(f"\nToken {token_data['symbol']} is expired (matured)")
                
                # Identify underlying token from config
                underlying_token = next(iter(token_data['underlying'].values()))
                print(f"Converting directly to underlying {underlying_token['symbol']} token (1:1)")
                
                # Direct conversion to underlying token (1:1)
                underlying_amount = balance_wei  # same amount due to same decimals
                
                # Convert underlying token to USDC via CoWSwap
                print(f"\nConverting {underlying_token['symbol']} to USDC via CoWSwap:")
                result = get_quote(
                    network="ethereum",
                    sell_token=underlying_token['address'],
                    buy_token=USDC_ADDRESS,
                    amount=str(underlying_amount),
                    token_decimals=underlying_token['decimals'],
                    token_symbol=underlying_token['symbol']
                )
                
                if result["quote"]:
                    usdc_amount = int(result["quote"]["quote"]["buyAmount"])
                    price_impact = float(result["conversion_details"].get("price_impact", "0"))
                    if isinstance(price_impact, str) and price_impact == "N/A":
                        price_impact = 0
                    return usdc_amount, price_impact/100
                
                raise Exception(f"Failed to convert {underlying_token['symbol']} to USDC")

            # If not expired, use existing code for Pendle API
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
            amount_out = int(data['amountOut'])
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
        
        print("\nProcessing network: ethereum")
        
        checksum_address = Web3.to_checksum_address(address)
        result = {"equilibria": {}}  # Initialize with complete structure
        
        try:
            # Get LP token position
            print(f"\nProcessing position: GHO-USR LP")
            
            # Contract information
            print("\nContract information:")
            print(f"  staking_contract: {self.pool_info['rewardPool']} (BaseRewardPoolV2)")
            print(f"  market: {self.pool_info['market']} (PendleMarket)")
            print(f"  booster: {self.pool_info['rewardPool']} (EquilibriaBooster)")
            
            # Get staked LP token balance
            print("\nQuerying staked LP token balance:")
            print(f"  Contract: {self.pool_info['rewardPool']} (BaseRewardPoolV2)")
            print("  Function: balanceOf(address) - Returns user's staked LP token balance")
            balance = self.get_staked_balance(address)
            
            if balance == 0:
                print("No staked LP balance found")
                return {"equilibria": {}}
            
            print(f"  Amount: {balance} (decimals: 18)")
            print(f"  Formatted: {(Decimal(balance) / Decimal(10**18)):.6f} GHO-USR LP")
            
            # Convert LP tokens to USDC
            print("\nConverting LP tokens to USDC:")
            print("  Method: Calling Pendle SDK remove-liquidity endpoint")
            print(f"  Market: {self.pool_info['market']}")
            usdc_amount, price_impact = self.get_remove_liquidity_data(balance)
            formatted_usdc = Decimal(usdc_amount) / Decimal(10**6)
            print("✓ Conversion successful:")
            print(f"  - USDC value: {formatted_usdc:.6f}")
            print(f"  - Price impact: {price_impact:.4f}%")
            
            # Get reward token balance
            print("\nQuerying reward token (PENDLE):")
            print(f"  Contract: {self.pool_info['rewardPool']} (BaseRewardPoolV2)")
            print("  Function: earned(address, token) - Returns pending PENDLE rewards")
            reward_balance = self.get_earned_rewards(address)['PENDLE']
            
            print(f"  Amount: {reward_balance} (decimals: 18)")
            print(f"  Formatted: {(Decimal(reward_balance) / Decimal(10**18)):.6f} PENDLE")
            
            # Convert rewards to USDC
            print("\nConverting rewards to USDC:")
            pendle_usdc_amount, pendle_price_impact, success, conversion_details = self.get_reward_value_in_usdc(
                "PENDLE", 
                str(reward_balance)
            )
            
            # Calculate totals
            print("\nCalculating USDC totals:")
            lp_total = usdc_amount
            rewards_total = pendle_usdc_amount
            total = lp_total + rewards_total
            
            print(f"  LP tokens: {lp_total/1e6:.6f} USDC")
            print(f"  Rewards: {rewards_total/1e6:.6f} USDC")
            print(f"  Total: {total/1e6:.6f} USDC")
            
            print("\n[Equilibria] Calculation complete")

            # Ensure structure exists before adding data
            if "ethereum" not in result["equilibria"]:
                result["equilibria"]["ethereum"] = {}

            result["equilibria"]["ethereum"] = {
                "GHO-USR": {
                    "staking_contract": self.pool_info['rewardPool'],
                    "amount": str(balance),
                    "decimals": 18,
                    "value": {
                        "USDC": {
                            "amount": usdc_amount,
                            "decimals": 6,
                            "conversion_details": {
                                "source": "Pendle SDK",
                                "price_impact": f"{price_impact:.6f}",
                                "rate": f"{formatted_usdc/Decimal(balance)*Decimal(10**12):.6f}",
                                "fee_percentage": "0.0000%",
                                "fallback": False,
                                "note": "Direct Conversion using Pendle SDK"
                            }
                        }
                    },
                    "rewards": {
                        "PENDLE": {
                            "amount": str(reward_balance),
                            "decimals": 18,
                            "value": {
                                "USDC": {
                                    "amount": pendle_usdc_amount,
                                    "decimals": 6,
                                    "conversion_details": conversion_details
                                }
                            }
                        }
                    }
                },
                "usdc_totals": {
                    "lp_tokens_total": {
                        "wei": lp_total,
                        "formatted": f"{lp_total/1e6:.6f}"
                    },
                    "rewards_total": {
                        "wei": rewards_total,
                        "formatted": f"{rewards_total/1e6:.6f}"
                    },
                    "total": {
                        "wei": total,
                        "formatted": f"{total/1e6:.6f}"
                    }
                }
            }

            # Add global total
            result["equilibria"]["usdc_totals"] = {
                "total": {
                    "wei": total,
                    "formatted": f"{total/1e6:.6f}"
                }
            }

        except Exception as e:
            print(f"✗ Error fetching Equilibria positions: {str(e)}")
            # In case of error, return a valid but empty structure
            return {"equilibria": {
                "usdc_totals": {
                    "total": {
                        "wei": 0,
                        "formatted": "0.000000"
                    }
                }
            }}

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
    
    # Display position summary
    if results and "equilibria" in results:
        data = results["equilibria"]
        if "ethereum" in data:
            position = data["ethereum"]["GHO-USR"]
            if "value" in position and "USDC" in position["value"]:
                print(f"equilibria.ethereum.GHO-USR: {position['value']['USDC']['amount']/1e6:.6f} USDC")
            if "rewards" in position:
                for token, reward in position["rewards"].items():
                    if "value" in reward and "USDC" in reward["value"]:
                        print(f"equilibria.ethereum.GHO-USR.rewards.{token}: {reward['value']['USDC']['amount']/1e6:.6f} USDC")
    
    print("\n" + "="*80)
    print("FINAL RESULT:")
    print("="*80 + "\n")
    print(json.dumps(results, indent=2))
