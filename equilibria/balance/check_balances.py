from web3 import Web3
from typing import Dict
import json
import os
import sys
from dotenv import load_dotenv

# Ajouter le répertoire racine au PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config.networks import RPC_URLS

# Charger les variables d'environnement
load_dotenv()

# LP Token ABI minimal pour balanceOf
LP_TOKEN_ABI = [
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

def get_equilibria_lp_balances(w3: Web3, wallet_address: str, chain_id: str) -> Dict[str, float]:
    """
    Get LP token balances for a wallet address on a specific network.
    
    Args:
        w3: Web3 instance
        wallet_address: Wallet address to check
        chain_id: Chain ID ("1" for Ethereum, "8453" for Base)
        
    Returns:
        Dict mapping market addresses to LP token balances
    """
    # Load markets configuration
    markets_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'markets', 'markets.json')
    with open(markets_path, 'r') as f:
        markets = json.load(f)
    
    network = "ethereum" if chain_id == "1" else "base" if chain_id == "8453" else None
    if not network or network not in markets:
        return {}
    
    balances = {}
    checksum_address = w3.to_checksum_address(wallet_address)
    
    for market in markets[network]['markets']:
        if not market['active']:
            continue
            
        try:
            # Create contract instance for LP token using market address
            lp_token = w3.eth.contract(
                address=w3.to_checksum_address(market['address']),
                abi=LP_TOKEN_ABI
            )
            
            # Get balance
            balance = lp_token.functions.balanceOf(checksum_address).call()
            if balance > 0:
                balances[market['address']] = float(balance) / 1e18  # Convert from wei to ETH
                
        except Exception as e:
            print(f"Error checking balance for market {market['address']}: {e}")
            continue
    
    return balances 