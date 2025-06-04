import json
from typing import Dict, List
from web3 import Web3
from eth_typing import Address
from decimal import Decimal

def load_market_mapping() -> Dict:
    """Load the market mapping from the JSON file."""
    with open('pendle/markets/market_mapping.json', 'r') as f:
        return json.load(f)

def get_pt_balances(w3: Web3, wallet_address: str, chain_id: str) -> Dict[str, dict]:
    """
    Get PT token balances for all markets in the market mapping for a specific chain.
    
    Args:
        w3: Web3 instance
        wallet_address: The wallet address to check balances for
        chain_id: The chain ID to filter markets by
        
    Returns:
        Dict mapping market addresses to their PT token balances and details
    """
    market_data = load_market_mapping()
    balances = {}
    
    # ERC20 ABI for balanceOf, symbol, and name functions
    erc20_abi = [
        {
            "constant": True,
            "inputs": [{"name": "_owner", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"name": "balance", "type": "uint256"}],
            "type": "function"
        },
        {
            "constant": True,
            "inputs": [],
            "name": "symbol",
            "outputs": [{"name": "", "type": "string"}],
            "type": "function"
        },
        {
            "constant": True,
            "inputs": [],
            "name": "name",
            "outputs": [{"name": "", "type": "string"}],
            "type": "function"
        }
    ]
    
    for market_address, market_info in market_data['markets'].items():
        # Only check markets on the specified chain
        if market_info['chain_id'] != chain_id:
            continue
            
        pt_token_address = market_info['tokens']['pt'].split('-')[1]  # Extract address from chain_id-address format
        contract = w3.eth.contract(address=Web3.to_checksum_address(pt_token_address), abi=erc20_abi)
        
        try:
            balance = contract.functions.balanceOf(Web3.to_checksum_address(wallet_address)).call()
            symbol = contract.functions.symbol().call()
            name = contract.functions.name().call()
            
            if balance > 0:
                balances[market_address] = {
                    "balance": Decimal(balance) / Decimal(10**18),  # Assuming 18 decimals
                    "token": {
                        "address": pt_token_address,
                        "symbol": symbol,
                        "name": name,
                        "decimals": 18
                    },
                    "market": market_info["name"]
                }
        except Exception as e:
            print(f"Error getting balance for market {market_address}: {str(e)}")
    
    return balances

def get_pendle_lp_balances(w3: Web3, wallet_address: str, chain_id: str) -> Dict[str, Decimal]:
    """
    Get PENDLE-LP token balances for all markets in the market mapping for a specific chain.
    
    Args:
        w3: Web3 instance
        wallet_address: The wallet address to check balances for
        chain_id: The chain ID to filter markets by
        
    Returns:
        Dict mapping market addresses to their PENDLE-LP token balances
    """
    market_data = load_market_mapping()
    balances = {}
    
    # ERC20 ABI for balanceOf function
    erc20_abi = [
        {
            "constant": True,
            "inputs": [{"name": "_owner", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"name": "balance", "type": "uint256"}],
            "type": "function"
        }
    ]
    
    for market_address, market_info in market_data['markets'].items():
        # Only check markets on the specified chain
        if market_info['chain_id'] != chain_id:
            continue
            
        # The market address itself is the LP token address
        contract = w3.eth.contract(address=Web3.to_checksum_address(market_address), abi=erc20_abi)
        
        try:
            balance = contract.functions.balanceOf(Web3.to_checksum_address(wallet_address)).call()
            balances[market_address] = Decimal(balance) / Decimal(10**18)  # Assuming 18 decimals
        except Exception as e:
            print(f"Error getting LP balance for market {market_address}: {str(e)}")
            balances[market_address] = Decimal('0')
    
    return balances 