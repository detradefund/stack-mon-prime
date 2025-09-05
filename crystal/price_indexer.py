from web3 import Web3
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional
from decimal import Decimal
import time

# Add parent directory to PYTHONPATH
root_path = str(Path(__file__).parent.parent)
sys.path.append(root_path)

from config.networks import RPC_URLS, NETWORK_TOKENS, CRYSTAL_POOLS

class CrystalPriceIndexer:
    """
    Crystal Price Indexer - Handles different pool types and real price fetching
    """
    
    def __init__(self, network: str = "monad"):
        self.network = network
        self.w3 = Web3(Web3.HTTPProvider(RPC_URLS[network]))
        
        # Crystal pool configurations from config
        self.crystal_pools = CRYSTAL_POOLS.get(network, {})
        
        # Initialize Crystal pool contracts
        self.pool_contracts = self._init_crystal_pool_contracts()
        
        print(f"=== Crystal Price Indexer Initialized ===")
        print(f"Network: {network}")
        print(f"RPC: {RPC_URLS[network]}")
        print(f"Found {len(self.crystal_pools)} Crystal pools")
    
    def _init_crystal_pool_contracts(self) -> Dict[str, Any]:
        """Initialize Crystal pool contracts"""
        contracts = {}
        
        # Crystal Pool ABI for getPrice() function
        pool_abi = [
            {
                "inputs": [],
                "name": "getPrice",
                "outputs": [
                    {"name": "price", "type": "uint256"},
                    {"name": "highestBid", "type": "uint256"},
                    {"name": "lowestAsk", "type": "uint256"}
                ],
                "stateMutability": "view",
                "type": "function"
            }
        ]
        
        # Initialize contracts for each Crystal pool
        for pool_name, pool_config in self.crystal_pools.items():
            pool_address = pool_config["pool_address"]
            try:
                contracts[pool_name] = {
                    "contract": self.w3.eth.contract(
                        address=Web3.to_checksum_address(pool_address),
                        abi=pool_abi
                    ),
                    "config": pool_config
                }
                print(f"✓ Crystal pool contract initialized for {pool_name}: {pool_address}")
            except Exception as e:
                print(f"✗ Failed to initialize Crystal pool for {pool_name}: {str(e)}")
                
        return contracts
    
    def get_pool_type(self, pool_name: str) -> str:
        """
        Determine pool type: 'usdc' or 'mon'
        """
        if pool_name not in self.crystal_pools:
            return "unknown"
        
        pool_config = self.crystal_pools[pool_name]
        quote_address = pool_config["quote_address"]
        
        # USDC address
        usdc_address = "0xf817257fed379853cDe0fa4F97AB987181B1E5Ea"
        # WMON address
        wmon_address = "0x760AfE86e5de5fa0Ee542fc7B7B713e1c5425701"
        
        if quote_address.lower() == usdc_address.lower():
            return "usdc"
        elif quote_address.lower() == wmon_address.lower():
            return "mon"
        else:
            return "unknown"
    
    def get_crystal_pool_price(self, pool_name: str) -> Optional[Decimal]:
        """
        Get price from Crystal pool contract using pool-specific scaling factors
        """
        try:
            if pool_name not in self.pool_contracts:
                return None
                
            pool_data = self.pool_contracts[pool_name]
            contract = pool_data["contract"]
            config = pool_data["config"]
            
            # Get scaling factor for this pool
            scaling_factor = config["scaling_factor"]
            
            # Call getPrice() function
            result = contract.functions.getPrice().call()
            raw_price = result[0]  # price field
            
            # Apply pool-specific scaling
            price = Decimal(raw_price) / Decimal(scaling_factor)
            return price
                
        except Exception as e:
            print(f"Error getting Crystal pool price for {pool_name}: {str(e)}")
            return None
    
    def get_all_crystal_prices(self) -> Dict[str, Any]:
        """
        Get all prices from Crystal pools
        """
        result = {}
        
        for pool_name, pool_config in self.crystal_pools.items():
            pool_type = self.get_pool_type(pool_name)
            price = self.get_crystal_pool_price(pool_name)
            
            if price is not None:
                # Extract base token from pool name
                base_token = pool_config["base_address"]
                
                result[pool_name] = {
                    "price": str(price),
                    "pool_type": pool_type,
                    "base_token": base_token,
                    "quote_token": pool_config["quote_address"],
                    "scaling_factor": pool_config["scaling_factor"],
                    "max_price": pool_config["max_price"],
                    "timestamp": int(time.time())
                }
        
        return result
    
    def get_token_price_in_mon(self, token_symbol: str) -> Optional[Decimal]:
        """
        Get token price in MON by checking all relevant pools
        """
        # First, find the token's address
        token_address = None
        for symbol, token_data in NETWORK_TOKENS[self.network].items():
            if symbol == token_symbol:
                token_address = token_data["address"]
                break
        
        if not token_address:
            return None
        
        # Check all pools for this token
        for pool_name, pool_config in self.crystal_pools.items():
            base_address = pool_config["base_address"]
            quote_address = pool_config["quote_address"]
            
            # If token is base token in this pool
            if base_address.lower() == token_address.lower():
                pool_type = self.get_pool_type(pool_name)
                price = self.get_crystal_pool_price(pool_name)
                
                if price is not None:
                    if pool_type == "mon":
                        # Already in MON
                        return price
                    elif pool_type == "usdc":
                        # Need to convert USDC to MON
                        mon_usdc_price = self.get_mon_usdc_price()
                        if mon_usdc_price and mon_usdc_price > 0:
                            return price / mon_usdc_price
        
        return None
    
    def get_mon_usdc_price(self) -> Optional[Decimal]:
        """
        Get MON/USDC price from Crystal pool
        """
        return self.get_crystal_pool_price("MON/USDC")
    
    def get_crystal_pool_addresses(self) -> Dict[str, str]:
        """
        Get all Crystal pool addresses from config
        """
        addresses = {}
        
        for pool_name, pool_config in self.crystal_pools.items():
            pool_address = pool_config["pool_address"]
            addresses[pool_name] = pool_address
            print(f"✓ {pool_name}: {pool_address}")
        
        return addresses
    
    def get_crystal_pool_configs(self) -> Dict[str, Any]:
        """
        Get all Crystal pool configurations
        """
        return self.crystal_pools
    
    def test_pool_connection(self, pool_name: str) -> bool:
        """
        Test if we can connect to a specific pool
        """
        if pool_name not in self.crystal_pools:
            print(f"✗ Pool {pool_name} not found in config")
            return False
        
        pool_config = self.crystal_pools[pool_name]
        pool_address = pool_config["pool_address"]
        
        try:
            # Simple test - just check if address is valid
            checksum_address = Web3.to_checksum_address(pool_address)
            print(f"✓ Pool {pool_name}: Valid address {checksum_address}")
            return True
        except Exception as e:
            print(f"✗ Pool {pool_name}: Invalid address - {str(e)}")
            return False

def main():
    """Test the Crystal Price Indexer"""
    print("=== Crystal Price Indexer Test ===")
    
    # Initialize Crystal indexer
    crystal = CrystalPriceIndexer("monad")
    
    # Get pool addresses
    print(f"\n=== Crystal Pool Addresses ===")
    addresses = crystal.get_crystal_pool_addresses()
    
    # Test pool connections
    print(f"\n=== Testing Pool Connections ===")
    for pool_name in addresses.keys():
        crystal.test_pool_connection(pool_name)
    
    # Test pool types
    print(f"\n=== Pool Types ===")
    for pool_name in crystal.crystal_pools.keys():
        pool_type = crystal.get_pool_type(pool_name)
        print(f"{pool_name}: {pool_type.upper()} pool")
    
    # Test getting all prices
    print(f"\n=== Getting All Crystal Prices ===")
    try:
        all_prices = crystal.get_all_crystal_prices()
        for pool_name, price_data in all_prices.items():
            print(f"{pool_name}: {price_data['price']} ({price_data['pool_type']})")
    except Exception as e:
        print(f"Error getting prices: {str(e)}")
    
    # Test MON/USDC price specifically
    print(f"\n=== MON/USDC Price ===")
    try:
        mon_usdc_price = crystal.get_mon_usdc_price()
        if mon_usdc_price:
            print(f"MON/USDC: {mon_usdc_price} USDC")
        else:
            print("Could not get MON/USDC price")
    except Exception as e:
        print(f"Error getting MON/USDC price: {str(e)}")

if __name__ == "__main__":
    main()
