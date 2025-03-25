from web3 import Web3
import json
from pathlib import Path
import sys
import os
from decimal import Decimal

# Add parent directory to PYTHONPATH
root_path = str(Path(__file__).parent.parent)
sys.path.append(root_path)

from config.networks import NETWORK_TOKENS, RPC_URLS

class SupplyReader:
    def __init__(self):
        # Load contract ABI
        contract_path = Path(__file__).parent / 'DeTrade-Core-USDC.json'
        with open(contract_path) as f:
            self.abi = json.load(f)
        
        # Connect to Base network
        self.w3 = Web3(Web3.HTTPProvider(RPC_URLS['base']))
        
        # Initialize contract using address from network config
        contract_address = NETWORK_TOKENS['base']['DTUSDC']['address']
        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=self.abi
        )
    
    def get_total_supply(self) -> str:
        """Get the total supply of DTUSDC tokens"""
        total_supply = self.contract.functions.totalSupply().call()
        return str(total_supply)

    def format_total_supply(self) -> str:
        """Get formatted total supply with decimals"""
        total_supply = self.get_total_supply()
        return f"{Decimal(total_supply) / Decimal('1000000000000000000'):.18f}"

def main():
    reader = SupplyReader()
    total_supply = reader.get_total_supply()
    
    print(f"DTUSDC Total Supply:")
    print(f"Raw: {total_supply}")

if __name__ == "__main__":
    main() 