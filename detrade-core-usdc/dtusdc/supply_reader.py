from web3 import Web3
import json
from pathlib import Path
import sys
import os
from decimal import Decimal

"""
DTUSDC token supply reader.
Provides functionality to read and format the total supply of DeTrade Core USDC tokens.
Used by balance managers to calculate share prices and portfolio values.
"""

# Add parent directory to PYTHONPATH
root_path = str(Path(__file__).parent.parent)
sys.path.append(root_path)

from config.networks import NETWORK_TOKENS, RPC_URLS

class SupplyReader:
    """
    Reads total supply information for DTUSDC token on Base network.
    Handles both raw and formatted supply values with proper decimal handling.
    """
    
    def __init__(self):
        # Load DTUSDC contract interface
        contract_path = Path(__file__).parent / 'DeTrade-Core-USDC.json'
        with open(contract_path) as f:
            self.abi = json.load(f)
        
        # Initialize Base network connection
        self.w3 = Web3(Web3.HTTPProvider(RPC_URLS['base']))
        
        # Setup DTUSDC contract instance
        contract_address = NETWORK_TOKENS['base']['DTUSDC']['address']
        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=self.abi
        )
    
    def get_total_supply(self) -> str:
        """
        Retrieves raw total supply of DTUSDC tokens.
        
        Returns:
            Total supply in wei (18 decimals) as string
        """
        total_supply = self.contract.functions.totalSupply().call()
        return str(total_supply)

    def format_total_supply(self) -> str:
        """
        Gets human-readable total supply with decimal formatting.
        
        Returns:
            Formatted total supply as string with 18 decimal places
            Example: "1000.000000000000000000" for 1000 DTUSDC
        """
        total_supply = self.get_total_supply()
        return f"{Decimal(total_supply) / Decimal('1000000000000000000'):.18f}"

def main():
    """
    CLI utility to check current DTUSDC total supply.
    Displays raw value in wei for verification purposes.
    """
    reader = SupplyReader()
    total_supply = reader.get_total_supply()
    
    print(f"DTUSDC Total Supply:")
    print(f"Raw: {total_supply}")

if __name__ == "__main__":
    main() 