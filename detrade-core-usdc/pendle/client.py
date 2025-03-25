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

# Add parent directory to PYTHONPATH
root_path = str(Path(__file__).parent.parent)
sys.path.append(root_path)

# Load environment variables from parent directory
load_dotenv(Path(root_path) / '.env')

class PendleClient(BaseProtocolClient):
    def __init__(self):
        # Initialize Web3 connections for each network
        self.eth_w3 = Web3(Web3.HTTPProvider(RPC_URLS['ethereum']))
        self.base_w3 = Web3(Web3.HTTPProvider(RPC_URLS['base']))
        
        # Initialize contracts for each Pendle token
        self.contracts = self._init_contracts()

    def _init_contracts(self):
        """Initialize contracts for all Pendle tokens across networks"""
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
        """Get balances for all Pendle tokens"""
        try:
            checksum_address = Web3.to_checksum_address(address)
            balances = {}
            
            # Iterate through networks and contracts to get balances
            for network, network_contracts in self.contracts.items():
                if network_contracts:  # If there are Pendle tokens on this network
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
        """Return empty balances structure for all Pendle tokens"""
        empty_balances = {}
        
        for network, tokens in NETWORK_TOKENS.items():
            network_tokens = {
                symbol: token_data for symbol, token_data in tokens.items() 
                if token_data.get('protocol') == 'pendle'
            }
            
            if network_tokens:  # If there are Pendle tokens on this network
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
        """Implementation of abstract method"""
        return [network for network, contracts in self.contracts.items() if contracts]
    
    def get_protocol_info(self) -> dict:
        """Implementation of abstract method"""
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
        """Get balance for a single token"""
        balances = self.get_balances(address)
        return balances[network][token_symbol]['amount'] if token_symbol in balances[network] else 0

if __name__ == "__main__":
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
            
            # Print human-readable balances for non-zero amounts
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