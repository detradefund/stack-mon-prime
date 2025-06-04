from web3 import Web3
from typing import Optional, Dict, Any
import json
import os
import sys
from dotenv import load_dotenv

# Ajouter le répertoire racine au PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config.networks import RPC_URLS

# Charger les variables d'environnement
load_dotenv()

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
    }
]

class StakeBalance:
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

    def get_staked_balance(self, address: str) -> Dict[str, Dict[str, Any]]:
        """
        Get staked balance for all markets across all networks
        """
        print(f"\nChecking balances for: {address}")
        checksum_address = Web3.to_checksum_address(address)
        results = {}

        for network, network_data in self.markets.items():
            results[network] = {}

            for market in network_data['markets']:
                if not market['active']:
                    continue

                try:
                    # Create contract instance with the correct base_reward_pool address for this network
                    reward_pool = self.w3_instances[network].eth.contract(
                        address=self.w3_instances[network].to_checksum_address(market['base_reward_pool']),
                        abi=BASE_REWARD_POOL_ABI
                    )

                    # Get balance
                    balance = reward_pool.functions.balanceOf(checksum_address).call()

                    if balance > 0:
                        results[network][market['name']] = {
                            "balance": balance,
                            "balance_in_eth": Web3.from_wei(balance, 'ether'),
                            "market_address": market['address'],
                            "base_reward_pool": market['base_reward_pool']
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
    stake_balance = StakeBalance()
    results = stake_balance.get_staked_balance(address)
    
    # Display results
    print("\n" + "="*50)
    print("STAKED BALANCES")
    print("="*50)
    
    for network, pools in results.items():
        if pools:  # Only show network if it has balances
            print(f"\n{network.upper()}:")
            for pool_name, data in pools.items():
                print(f"- {pool_name}: {data['balance_in_eth']} ETH")
                print(f"  Market: {data['market_address']}")
                print(f"  Pool: {data['base_reward_pool']}")
                print() 