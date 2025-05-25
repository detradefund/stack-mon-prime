"""
Curve Protocol pools configuration and utilities.
Contains pool addresses and related constants for different networks.
"""

from typing import Dict

# Pool addresses for different networks
CURVE_POOLS: Dict[str, Dict[str, Dict[str, str]]] = {
    "ethereum": {
        # Add Ethereum pool addresses here
    },
    "base": {
        "cbeth-f": {
            "pool": "0x11C1fBd4b3De66bC0565779b35171a6CF3E71f59",  # Pool address
            "lp_token": "0x98244d93D42b42aB3E3A4D12A5dc0B3e7f8F32f9",  # Curve.fi Factory Crypto Pool: cbETH/WETH (cbeth-f)
            "gauge": "0xE9c898BA654deC2bA440392028D2e7A194E6dc3e",
            "abi": "Vyper_contract"  # Using Vyper contract ABI
        }
    }
}

def get_pool_address(network: str, pool_name: str) -> str:
    """
    Get the address of a Curve pool for a specific network.
    
    Args:
        network: Network identifier ('ethereum' or 'base')
        pool_name: Name of the pool
        
    Returns:
        Pool address as string
    """
    if network not in CURVE_POOLS:
        raise ValueError(f"Network {network} not supported")
    
    if pool_name not in CURVE_POOLS[network]:
        raise ValueError(f"Pool {pool_name} not found for network {network}")
        
    return CURVE_POOLS[network][pool_name]["pool"]

def get_gauge_address(network: str, pool_name: str) -> str:
    """
    Get the address of a Curve gauge for a specific network.
    
    Args:
        network: Network identifier ('ethereum' or 'base')
        pool_name: Name of the pool
        
    Returns:
        Gauge address as string
    """
    if network not in CURVE_POOLS:
        raise ValueError(f"Network {network} not supported")
    
    if pool_name not in CURVE_POOLS[network]:
        raise ValueError(f"Pool {pool_name} not found for network {network}")
        
    return CURVE_POOLS[network][pool_name]["gauge"]

def get_lp_token_address(network: str, pool_name: str) -> str:
    """
    Get the address of a Curve LP token for a specific network.
    
    Args:
        network: Network identifier ('ethereum' or 'base')
        pool_name: Name of the pool
        
    Returns:
        LP token address as string
    """
    if network not in CURVE_POOLS:
        raise ValueError(f"Network {network} not supported")
    
    if pool_name not in CURVE_POOLS[network]:
        raise ValueError(f"Pool {pool_name} not found for network {network}")
        
    return CURVE_POOLS[network][pool_name]["lp_token"]

def get_pool_abi(network: str, pool_name: str) -> str:
    """
    Get the ABI name to use for a Curve pool.
    
    Args:
        network: Network identifier ('ethereum' or 'base')
        pool_name: Name of the pool
        
    Returns:
        ABI name as string
    """
    if network not in CURVE_POOLS:
        raise ValueError(f"Network {network} not supported")
    
    if pool_name not in CURVE_POOLS[network]:
        raise ValueError(f"Pool {pool_name} not found for network {network}")
        
    return CURVE_POOLS[network][pool_name]["abi"] 