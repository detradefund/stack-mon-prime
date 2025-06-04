"""
Curve Protocol balance manager.
Handles interactions with Curve pools and manages token balances.
"""

from typing import Dict, Optional, List, Tuple, Any
from decimal import Decimal
import json
from pathlib import Path
import sys
from web3 import Web3
import argparse
import time
from datetime import datetime
import os
from dotenv import load_dotenv

# Add parent directory to PYTHONPATH
sys.path.append(str(Path(__file__).parent.parent.parent))

from cowswap.cow_client import get_quote
from config.networks import NETWORK_TOKENS, RPC_URLS
from utils.retry import APIRetry

# Load environment variables
load_dotenv()

# Get production address from environment variable
DEFAULT_ADDRESS = os.getenv('PRODUCTION_ADDRESS', "0x66DbceE7feA3287B3356227d6F3DfF3CeFbC6F3C")

# Load markets configuration
MARKETS_PATH = Path(__file__).parent.parent / "markets" / "markets.json"
with open(MARKETS_PATH) as f:
    MARKETS_CONFIG = json.load(f)

def get_pool_address(network: str, pool_name: str) -> str:
    """Get pool address from markets.json"""
    return MARKETS_CONFIG["pool_address"]

def get_gauge_address(network: str, pool_name: str) -> str:
    """Get gauge address from markets.json"""
    return MARKETS_CONFIG["gauge"]

def get_lp_token_address(network: str, pool_name: str) -> str:
    """Get LP token address from markets.json"""
    return MARKETS_CONFIG["lp_token"]

def get_pool_abi(network: str, pool_name: str) -> str:
    """Get pool ABI name from markets.json"""
    return MARKETS_CONFIG["abi"]

class CurveBalanceManager:
    """
    Manages Curve Protocol interactions and balance tracking.
    """
    
    def __init__(self, network: str, w3: Web3):
        """
        Initialize the Curve balance manager.
        
        Args:
            network: Network identifier ('ethereum' or 'base')
            w3: Web3 instance for blockchain interaction
        """
        self.network = network
        self.w3 = w3
        self.network_tokens = NETWORK_TOKENS
        self.abis_path = Path(__file__).parent.parent / "abis"
        
    def get_gauge_balance(self, pool_name: str, user_address: str) -> Decimal:
        """
        Get the balance of LP tokens staked in a gauge.
        
        Args:
            pool_name: Name of the pool
            user_address: Address of the user
            
        Returns:
            Staked LP token balance
        """
        gauge_address = get_gauge_address(self.network, pool_name)
        
        # Load Child Liquidity Gauge ABI
        with open(self.abis_path / "Child Liquidity Gauge.json") as f:
            gauge_abi = json.load(f)
            
        gauge_contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(gauge_address),
            abi=gauge_abi
        )
        
        balance = gauge_contract.functions.balanceOf(
            self.w3.to_checksum_address(user_address)
        ).call()
        
        return Decimal(balance)
        
    def get_pool_balance(self, pool_name: str) -> Dict[str, Decimal]:
        """
        Get the current balance of tokens in a Curve pool.
        
        Args:
            pool_name: Name of the pool
            
        Returns:
            Dictionary of token balances in the pool
        """
        pool_address = get_pool_address(self.network, pool_name)
        abi_name = get_pool_abi(self.network, pool_name)
        
        # Load pool ABI
        with open(self.abis_path / f"{abi_name}.json") as f:
            pool_abi = json.load(f)
            
        pool_contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(pool_address),
            abi=pool_abi
        )
        
        # For Vyper contracts, we need to get balances one by one
        balances = {}
        for i in range(2):  # This pool has 2 tokens
            balance = pool_contract.functions.balances(i).call()
            if balance > 0:
                balances[str(i)] = Decimal(balance)
                
        return balances
        
    def get_token_price(self, token_address: str, pool_name: str) -> Decimal:
        """
        Get the price of a token from a Curve pool.
        
        Args:
            token_address: Address of the token
            pool_name: Name of the pool to use for price discovery
            
        Returns:
            Token price in USD
        """
        pool_address = get_pool_address(self.network, pool_name)
        abi_name = get_pool_abi(self.network, pool_name)
        
        # Load pool ABI
        with open(self.abis_path / f"{abi_name}.json") as f:
            pool_abi = json.load(f)
            
        pool_contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(pool_address),
            abi=pool_abi
        )
        
        virtual_price = pool_contract.functions.get_virtual_price().call()
        return Decimal(virtual_price) / Decimal(10**18)
        
    def get_lp_token_balance(self, pool_name: str, user_address: str) -> Decimal:
        """
        Get the LP token balance for a user in a specific pool.
        
        Args:
            pool_name: Name of the pool
            user_address: Address of the user
            
        Returns:
            LP token balance
        """
        lp_token_address = get_lp_token_address(self.network, pool_name)
        
        # Load ERC20 ABI
        with open(self.abis_path / "erc20.json") as f:
            erc20_abi = json.load(f)
            
        lp_token_contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(lp_token_address),
            abi=erc20_abi["abi"]
        )
        
        balance = lp_token_contract.functions.balanceOf(
            self.w3.to_checksum_address(user_address)
        ).call()
        
        return Decimal(balance)
        
    def get_pool_tvl(self, pool_name: str) -> Decimal:
        """
        Get the Total Value Locked (TVL) in a Curve pool.
        
        Args:
            pool_name: Name of the pool
            
        Returns:
            TVL in USD
        """
        pool_address = get_pool_address(self.network, pool_name)
        lp_token_address = get_lp_token_address(self.network, pool_name)
        abi_name = get_pool_abi(self.network, pool_name)
        
        # Load pool ABI for virtual price
        with open(self.abis_path / f"{abi_name}.json") as f:
            pool_abi = json.load(f)
            
        pool_contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(pool_address),
            abi=pool_abi
        )
        
        # Load ERC20 ABI for total supply
        with open(self.abis_path / "erc20.json") as f:
            erc20_abi = json.load(f)
            
        lp_token_contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(lp_token_address),
            abi=erc20_abi["abi"]
        )
        
        virtual_price = pool_contract.functions.get_virtual_price().call()
        total_supply = lp_token_contract.functions.totalSupply().call()
        
        return (Decimal(virtual_price) * Decimal(total_supply)) / Decimal(10**18)

    def get_lp_token_total_supply(self, pool_name: str) -> Decimal:
        """
        Get the total supply of LP tokens for a pool from the Child Liquidity Gauge.
        
        Args:
            pool_name: Name of the pool
            
        Returns:
            Total supply of LP tokens
        """
        gauge_address = get_gauge_address(self.network, pool_name)
        
        # Load Child Liquidity Gauge ABI
        with open(self.abis_path / "Child Liquidity Gauge.json") as f:
            gauge_abi = json.load(f)
            
        gauge_contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(gauge_address),
            abi=gauge_abi
        )
        
        total_supply = gauge_contract.functions.totalSupply().call()
        return Decimal(total_supply)

    def get_ownership_percentage(self, pool_name: str, user_address: str) -> Decimal:
        """
        Calculate the percentage of LP tokens owned by an address.
        
        Args:
            pool_name: Name of the pool
            user_address: Address of the user
            
        Returns:
            Percentage of LP tokens owned (0-100) with maximum precision
        """
        balance = self.get_gauge_balance(pool_name, user_address)
        total_supply = self.get_lp_token_total_supply(pool_name)
        
        if total_supply == 0:
            return Decimal('0')
            
        # Calculate ownership with maximum precision
        return (balance / total_supply) * Decimal('100')

    def get_pool_tokens(self, pool_name: str) -> List[Tuple[str, str]]:
        """
        Get the tokens in a Curve pool with their symbols.
        
        Args:
            pool_name: Name of the pool
            
        Returns:
            List of tuples containing (token_address, token_symbol)
        """
        pool_address = get_pool_address(self.network, pool_name)
        abi_name = get_pool_abi(self.network, pool_name)
        
        # Load pool ABI
        with open(self.abis_path / f"{abi_name}.json") as f:
            pool_abi = json.load(f)
            
        pool_contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(pool_address),
            abi=pool_abi
        )
        
        # Get token addresses from pool
        token_addresses = []
        for i in range(2):  # This pool has 2 tokens
            token_address = pool_contract.functions.coins(i).call()
            token_addresses.append(token_address)
            
        # Map addresses to symbols using NETWORK_TOKENS
        token_info = []
        for addr in token_addresses:
            addr_lower = addr.lower()
            symbol = "UNKNOWN"
            
            # Search for token in NETWORK_TOKENS
            for token_name, token_data in NETWORK_TOKENS[self.network].items():
                if token_data["address"].lower() == addr_lower:
                    symbol = token_data["symbol"]
                    break
                    
            token_info.append((addr, symbol))
            
        return token_info

    def get_pool_balances(self, pool_name: str) -> List[Tuple[str, str, Decimal]]:
        """
        Get the balances of tokens in a Curve pool.
        
        Args:
            pool_name: Name of the pool
            
        Returns:
            List of tuples containing (token_address, token_symbol, balance)
        """
        pool_address = get_pool_address(self.network, pool_name)
        abi_name = get_pool_abi(self.network, pool_name)
        
        # Load pool ABI
        with open(self.abis_path / f"{abi_name}.json") as f:
            pool_abi = json.load(f)
            
        pool_contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(pool_address),
            abi=pool_abi
        )
        
        # Get token addresses and balances
        token_info = []
        for i in range(2):  # This pool has 2 tokens
            token_address = pool_contract.functions.coins(i).call()
            balance = pool_contract.functions.balances(i).call()
            
            # Get token symbol
            addr_lower = token_address.lower()
            symbol = "UNKNOWN"
            decimals = 18  # Default to 18 decimals
            
            # Search for token in NETWORK_TOKENS
            for token_name, token_data in NETWORK_TOKENS[self.network].items():
                if token_data["address"].lower() == addr_lower:
                    symbol = token_data["symbol"]
                    decimals = token_data["decimals"]
                    break
            
            token_info.append((token_address, symbol, Decimal(balance) / Decimal(10**decimals)))
            
        return token_info

    def get_user_balances(self, pool_name: str, user_address: str) -> List[Tuple[str, str, Decimal]]:
        """
        Get the user's share of tokens in a Curve pool based on ownership percentage.
        Calculates exact token amounts with maximum precision.
        
        Args:
            pool_name: Name of the pool
            user_address: Address of the user
            
        Returns:
            List of tuples containing (token_address, token_symbol, user_balance) with maximum precision
        """
        # Get ownership percentage with maximum precision
        ownership = self.get_ownership_percentage(pool_name, user_address)
        pool_balances = self.get_pool_balances(pool_name)
        
        user_balances = []
        for addr, symbol, balance in pool_balances:
            # Calculate user's share with maximum precision
            # Divide by 100 since ownership is in percentage
            user_balance = (balance * ownership) / Decimal('100')
            user_balances.append((addr, symbol, user_balance))
            
        return user_balances

def main():
    """
    Main function to test the Curve balance manager.
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Check Curve gauge balance')
    parser.add_argument('--address', type=str, default=DEFAULT_ADDRESS,
                      help=f'Address to check (default: {DEFAULT_ADDRESS})')
    args = parser.parse_args()
    
    # Initialize Web3 connection to Base using RPC from .env
    w3 = Web3(Web3.HTTPProvider(RPC_URLS["base"]))
    
    if not w3.is_connected():
        print("Failed to connect to Base network")
        return
        
    # Initialize balance manager
    manager = CurveBalanceManager("base", w3)
    
    try:
        print("\n" + "="*80)
        print("CURVE BALANCE MANAGER")
        print("="*80)
        
        # Get gauge balance for cbeth-f pool
        balance = manager.get_gauge_balance("cbeth-f", args.address)
        total_supply = manager.get_lp_token_total_supply("cbeth-f")
        ownership_percentage = manager.get_ownership_percentage("cbeth-f", args.address)
        pool_tokens = manager.get_pool_tokens("cbeth-f")
        pool_balances = manager.get_pool_balances("cbeth-f")
        user_balances = manager.get_user_balances("cbeth-f", args.address)
        
        print(f"\nCurve.fi cbeth-f Gauge Balance:")
        print(f"Address: {args.address}")
        print(f"Balance: {balance / Decimal(10**18):.6f} LP tokens")
        print(f"Total Supply: {total_supply / Decimal(10**18):.6f} LP tokens")
        print(f"Ownership: {ownership_percentage:.6f}%")
        
        print("\nPool Tokens:")
        for addr, symbol in pool_tokens:
            print(f"- {symbol}: {addr}")
            
        print("\nPool Balances:")
        for addr, symbol, balance in pool_balances:
            print(f"- {symbol}:")
            print(f"  Amount: {balance:.6f} {symbol}")
            
        print("\nUser Balances:")
        for addr, symbol, balance in user_balances:
            print(f"- {symbol}:")
            print(f"  Amount: {balance:.6f} {symbol}")
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 