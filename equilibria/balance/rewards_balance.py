from web3 import Web3
from typing import Dict, Any, List
import json
import os
import sys
from decimal import Decimal
from dotenv import load_dotenv

# Ajouter le répertoire racine au PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config.networks import RPC_URLS, NETWORK_TOKENS
from cowswap.cow_client import get_cowswap_quote

# Charger les variables d'environnement
load_dotenv()

# BaseRewardPoolV2 ABI pour les rewards
BASE_REWARD_POOL_ABI = [
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
        "inputs": [],
        "name": "getRewardTokens",
        "outputs": [{"internalType": "address[]", "name": "", "type": "address[]"}],
        "stateMutability": "view",
        "type": "function"
    }
]

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

class RewardsBalance:
    def __init__(self):
        # Initialize Web3 instances for each network
        self.w3_instances = {}
        for network, rpc in RPC_URLS.items():
            if not rpc:
                raise ValueError(f"{network.upper()}_RPC not configured in .env file")
            self.w3_instances[network] = Web3(Web3.HTTPProvider(rpc))
            if not self.w3_instances[network].is_connected():
                raise ValueError(f"Could not connect to {network} RPC")

        # Load markets configuration
        self.markets = self._load_markets()

    def _load_markets(self) -> Dict:
        """Load markets configuration from JSON file"""
        markets_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'markets', 'markets.json')
        with open(markets_path, 'r') as f:
            return json.load(f)

    def get_rewards_balance(self, address: str) -> Dict[str, Dict[str, Any]]:
        """
        Get rewards balance for all markets across all networks and convert to WETH value
        """
        print(f"\nChecking rewards for: {address}")
        checksum_address = Web3.to_checksum_address(address)
        results = {}

        for network, network_data in self.markets.items():
            results[network] = {}

            # Get WETH address for the current network
            weth_address = NETWORK_TOKENS[network]['WETH']['address']

            for market in network_data['markets']:
                if not market['active']:
                    continue

                try:
                    # Create contract instance with the correct base_reward_pool address
                    reward_pool = self.w3_instances[network].eth.contract(
                        address=self.w3_instances[network].to_checksum_address(market['base_reward_pool']),
                        abi=BASE_REWARD_POOL_ABI
                    )

                    # Get list of reward tokens
                    reward_tokens = reward_pool.functions.getRewardTokens().call()
                    
                    if not reward_tokens:
                        continue

                    market_rewards = {}
                    total_weth_value = Decimal('0')

                    for reward_token in reward_tokens:
                        try:
                            # Get earned rewards for each token
                            earned = reward_pool.functions.earned(
                                checksum_address,
                                reward_token
                            ).call()

                            if earned > 0:
                                print(f"\nProcessing reward token {reward_token}:")
                                print(f"  Earned amount: {format_amount(earned)} tokens")
                                
                                cowswap_result = get_cowswap_quote(
                                    network=network,
                                    sell_token=reward_token,
                                    buy_token=weth_address,
                                    amount=str(earned),
                                    sell_decimals=18,
                                    buy_decimals=18
                                )

                                weth_value = Decimal('0')
                                conversion_details = {
                                    "source": "Failed",
                                    "price_impact": "N/A",
                                    "rate": "0",
                                    "fee_percentage": "N/A",
                                    "fallback": True,
                                    "note": "Quote failed"
                                }

                                if cowswap_result and isinstance(cowswap_result, dict):
                                    if 'quote' in cowswap_result and cowswap_result['quote']:
                                        quote = cowswap_result['quote']
                                        if 'quote' in quote and 'buyAmount' in quote['quote']:
                                            weth_value = Decimal(quote['quote']['buyAmount']) / Decimal('1e18')
                                            total_weth_value += weth_value
                                            print(f"  Value in WETH: {format_amount(weth_value)}")
                                    
                                    if 'conversion_details' in cowswap_result:
                                        conversion_details = cowswap_result['conversion_details']

                                # Get token symbol from config if available
                                token_symbol = "UNKNOWN"
                                for token_name, token_info in NETWORK_TOKENS[network].items():
                                    if token_info['address'].lower() == reward_token.lower():
                                        token_symbol = token_name
                                        break

                                market_rewards[reward_token] = {
                                    "amount": str(earned),
                                    "decimals": 18,
                                    "symbol": token_symbol,
                                    "value": {
                                        "WETH": {
                                            "amount": str(int(weth_value * Decimal('1e18'))),
                                            "decimals": 18,
                                            "conversion_details": conversion_details
                                        }
                                    }
                                }
                        except Exception as e:
                            print(f"Error processing reward token {reward_token}: {e}")
                            continue

                    if market_rewards:
                        results[network][market['name']] = {
                            "market_address": market['address'],
                            "base_reward_pool": market['base_reward_pool'],
                            "rewards": market_rewards,
                            "value": {
                                "WETH": {
                                    "amount": str(int(total_weth_value * Decimal('1e18'))),
                                    "decimals": 18,
                                    "conversion_details": {
                                        "source": "CoWSwap",
                                        "price_impact": "0",
                                        "rate": str(total_weth_value / (Decimal(earned) / Decimal('1e18'))) if earned > 0 else "0",
                                        "fee_percentage": "0",
                                        "fallback": False,
                                        "note": "Direct CoWSwap quote"
                                    }
                                }
                            },
                            "totals": {
                                "wei": str(int(total_weth_value * Decimal('1e18'))),
                                "formatted": format_amount(str(total_weth_value))
                            }
                        }

                except Exception as e:
                    print(f"Error on {network} - {market['name']}: {e}")
                    continue

        return results

if __name__ == "__main__":
    # Get address from command line or use default
    address = sys.argv[1] if len(sys.argv) > 1 else os.getenv('PRODUCTION_ADDRESS')
    if not address:
        raise ValueError("No address provided and PRODUCTION_ADDRESS not found in .env file")

    # Initialize and run
    rewards_balance = RewardsBalance()
    results = rewards_balance.get_rewards_balance(address)
    
    # Print JSON structure
    print(json.dumps(results, indent=2)) 