import sys
import os
from pathlib import Path
from datetime import datetime
from web3 import Web3
import json
from dotenv import load_dotenv
from config.networks import NETWORK_TOKENS, RPC_URLS
from .abis import PT_ABI
from config.base_client import BaseProtocolClient

"""
Pendle Protocol client implementation.
Provides low-level interaction with Pendle Principal Tokens (PT) across networks.
Handles contract initialization, balance checking, and metadata retrieval.
"""

# Add parent directory to PYTHONPATH
root_path = str(Path(__file__).parent.parent)
sys.path.append(root_path)

# Load environment variables from parent directory
load_dotenv(Path(root_path) / '.env')

class PendleClient(BaseProtocolClient):
    """
    Core client for interacting with Pendle Protocol contracts.
    Implements BaseProtocolClient interface for standardized protocol integration.
    Manages PT token contracts across Ethereum and Base networks.
    """
    
    def __init__(self):
        # Initialize network-specific Web3 connections
        self.eth_w3 = Web3(Web3.HTTPProvider(RPC_URLS['ethereum']))
        self.base_w3 = Web3(Web3.HTTPProvider(RPC_URLS['base']))
        
        # Setup PT token contract instances
        self.contracts = self._init_contracts()

    def _init_contracts(self):
        """
        Initializes Web3 contract instances for all Pendle PT tokens.
        
        Returns:
            Dict mapping networks to their PT token contracts:
            {
                'ethereum': {'PT-Token1': Contract, ...},
                'base': {'PT-Token2': Contract, ...}
            }
        """
        contracts = {}
        
        for network, tokens in NETWORK_TOKENS.items():
            contracts[network] = {}
            w3 = self.eth_w3 if network == 'ethereum' else self.base_w3
            
            for token_symbol, token_data in tokens.items():
                if token_data.get('protocol') == 'pendle':
                    contracts[network][token_symbol] = w3.eth.contract(
                        address=Web3.to_checksum_address(token_data['address']),
                        abi=PT_ABI
                    )
        
        return contracts

    def get_balances(self, address: str) -> dict:
        """
        Retrieves balances for all PT tokens across networks.
        
        Args:
            address: Ethereum address to check balances for
            
        Returns:
            Nested dict containing:
            - Network-level balances
            - Token amounts and metadata
            - Underlying token information
            - Market and expiry details
        """
        try:
            checksum_address = Web3.to_checksum_address(address)
            balances = {}
            
            # Process each network's PT tokens
            for network, network_contracts in self.contracts.items():
                if network_contracts:  # Skip networks without PT tokens
                    balances[network] = {}
                    
                    for token_symbol, contract in network_contracts.items():
                        token_data = NETWORK_TOKENS[network][token_symbol]
                        balance = contract.functions.balanceOf(checksum_address).call()
                        
                        balances[network][token_symbol] = {
                            "amount": str(balance),
                            "decimals": token_data["decimals"],
                            "value": {
                                "raw": str(balance)
                            },
                            "metadata": {
                                "expiry": token_data["expiry"],
                                "market": token_data["market"],
                                "underlying": {
                                    "symbol": next(iter(token_data["underlying"].keys())),
                                    "address": next(iter(token_data["underlying"].values()))["address"]
                                }
                            }
                        }
            
            return balances
            
        except Exception as e:
            print(f"Error getting Pendle balances: {e}")
            return self._get_empty_balances()

    def _get_empty_balances(self) -> dict:
        """
        Creates empty balance structure for error handling.
        Maintains consistent response format even when balance fetching fails.
        
        Returns:
            Dict with zero balances but complete token metadata
        """
        empty_balances = {}
        
        for network, tokens in NETWORK_TOKENS.items():
            network_tokens = {
                symbol: token_data for symbol, token_data in tokens.items() 
                if token_data.get('protocol') == 'pendle'
            }
            
            if network_tokens:  # Skip networks without PT tokens
                empty_balances[network] = {}
                
                for token_symbol, token_data in network_tokens.items():
                    empty_balances[network][token_symbol] = {
                        "amount": "0",
                        "decimals": token_data["decimals"],
                        "value": {
                            "raw": "0"
                        },
                        "metadata": {
                            "expiry": token_data["expiry"],
                            "market": token_data["market"],
                            "underlying": {
                                "symbol": next(iter(token_data["underlying"].keys())),
                                "address": next(iter(token_data["underlying"].values()))["address"]
                            }
                        }
                    }
                    
        return empty_balances

    def get_supported_networks(self) -> list:
        """
        Lists networks where Pendle PT tokens are available.
        Required by BaseProtocolClient interface.
        """
        return [network for network, contracts in self.contracts.items() if contracts]
    
    def get_protocol_info(self) -> dict:
        """
        Provides protocol metadata and supported tokens.
        Required by BaseProtocolClient interface.
        
        Returns:
            Dict containing protocol name and supported token details
        """
        protocol_tokens = {}
        
        for network, tokens in NETWORK_TOKENS.items():
            for symbol, data in tokens.items():
                if data.get('protocol') == 'pendle':
                    protocol_tokens[symbol] = data
        
        return {
            "name": "Pendle",
            "tokens": protocol_tokens
        }

    def get_balance(self, network: str, token_symbol: str, address: str) -> int:
        """
        Retrieves balance for a specific PT token.
        
        Args:
            network: Network identifier ('ethereum' or 'base')
            token_symbol: PT token symbol
            address: Wallet address to check
            
        Returns:
            Token balance in wei
        """
        balances = self.get_balances(address)
        return balances[network][token_symbol]['amount'] if token_symbol in balances[network] else 0

if __name__ == "__main__":
    """
    Test script for PendleClient functionality.
    Tests balance fetching with known addresses and environment-configured address.
    """
    # Test addresses
    test_addresses = [
        "0xc6835323372a4393b90bcc227c58e82d45ce4b7d",  # Known address
        os.getenv('DEFAULT_USER_ADDRESS'),  # Address from .env
    ]
    
    client = PendleClient()
    print("PendleClient initialized")
    print(f"\nSupported networks: {client.get_supported_networks()}")
    
    for addr in test_addresses:
        if not addr:
            continue
            
        print(f"\nTesting with address: {addr}")
        try:
            balances = client.get_balances(addr)
            print("\nBalances:")
            print(json.dumps(balances, indent=2))
            
            # Display human-readable balances for non-zero positions
            print("\nNon-zero balances:")
            for network, tokens in balances.items():
                for token, data in tokens.items():
                    amount = int(data['amount'])
                    if amount > 0:
                        human_amount = amount / 10**data['decimals']
                        print(f"{network} - {token}: {human_amount}")
                        
        except Exception as e:
            print(f"Error occurred: {str(e)}")
            import traceback
            traceback.print_exc() 