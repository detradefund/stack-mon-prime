"""
Native token conversion utilities using protocol contract functions.
Supports wstETH (via stEthPerToken) and pufETH (via convertToAssets).
"""

import sys
from pathlib import Path
from web3 import Web3
from decimal import Decimal
import os

# Add parent directory to PYTHONPATH
sys.path.append(str(Path(__file__).parent.parent))

from config.networks import NETWORK_TOKENS, RPC_URLS

# Contract ABIs for native conversions
WSTETH_ABI = [
    {
        "inputs": [],
        "name": "stEthPerToken",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

PUFETH_ABI = [
    {
        "inputs": [{"internalType": "uint256", "name": "shares", "type": "uint256"}],
        "name": "convertToAssets",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# Configuration for native conversions
class ConversionConfig:
    """Configuration for choosing conversion methods based on context"""
    
    @classmethod 
    def should_use_native_for_spot(cls):
        """
        For SPOT assets, always use native conversion when available.
        No user interaction required.
        """
        return True
    
    @classmethod
    def should_use_native_for_euler(cls):
        """
        For EULER assets, always use market prices (CowSwap).
        This maintains consistency with market-based valuations.
        """
        return False

def convert_wsteth_to_weth(wsteth_amount: str, network: str = "ethereum") -> dict:
    """
    Convert wstETH to WETH using native Lido stEthPerToken() function.
    
    Args:
        wsteth_amount: Amount of wstETH in wei (as string)
        network: Network to use (default: "ethereum")
        
    Returns:
        dict: Conversion result with amount and details
    """
    try:
        if network != "ethereum":
            raise ValueError("wstETH conversion only supported on Ethereum mainnet")
            
        # Get RPC connection
        rpc_url = RPC_URLS[network]
        if not rpc_url:
            raise ValueError(f"No RPC URL configured for {network}")
            
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not w3.is_connected():
            raise ValueError(f"Cannot connect to {network} RPC")
            
        # Get wstETH contract address
        wsteth_address = NETWORK_TOKENS[network]["wstETH"]["address"]
        
        # Create contract instance
        wsteth_contract = w3.eth.contract(
            address=w3.to_checksum_address(wsteth_address),
            abi=WSTETH_ABI
        )
        
        # Get stETH per token rate
        steth_per_token = wsteth_contract.functions.stEthPerToken().call()
        
        # Calculate stETH amount
        wsteth_amount_decimal = Decimal(wsteth_amount)
        steth_per_token_decimal = Decimal(steth_per_token)
        
        # stETH amount = wstETH amount * stETH per token rate / 1e18
        steth_amount = (wsteth_amount_decimal * steth_per_token_decimal) // Decimal(10**18)
        
        # For this conversion, we assume stETH ≈ ETH ≈ WETH (1:1 ratio)
        # In practice, stETH trades very close to ETH with minimal slippage
        weth_amount = steth_amount
        
        # Calculate conversion rate
        rate = steth_per_token_decimal / Decimal(10**18)
        
        return {
            "quote": {
                "quote": {
                    "buyAmount": str(int(weth_amount)),
                    "sellAmount": wsteth_amount,
                    "feeAmount": "0"
                }
            },
            "conversion_details": {
                "source": "Lido wstETH.stEthPerToken()",
                "price_impact": "0.0000",  # Native conversion has no price impact
                "rate": str(rate),
                "fee_percentage": "0.0000",
                "fallback": False,
                "note": f"Native wstETH conversion using stEthPerToken() = {rate:.6f}",
                "steth_per_token": str(steth_per_token)
            }
        }
        
    except Exception as e:
        return {
            "quote": None,
            "conversion_details": {
                "source": "Error",
                "price_impact": "N/A",
                "rate": "0",
                "fee_percentage": "N/A",
                "fallback": True,
                "note": f"wstETH native conversion failed: {str(e)[:200]}"
            }
        }

def convert_pufeth_to_weth(pufeth_amount: str, network: str = "ethereum") -> dict:
    """
    Convert pufETH to WETH using native Puffer convertToAssets() function.
    
    Args:
        pufeth_amount: Amount of pufETH in wei (as string)
        network: Network to use (default: "ethereum")
        
    Returns:
        dict: Conversion result with amount and details
    """
    try:
        if network != "ethereum":
            raise ValueError("pufETH conversion only supported on Ethereum mainnet")
            
        # Get RPC connection
        rpc_url = RPC_URLS[network]
        if not rpc_url:
            raise ValueError(f"No RPC URL configured for {network}")
            
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not w3.is_connected():
            raise ValueError(f"Cannot connect to {network} RPC")
            
        # Get pufETH contract address
        pufeth_address = NETWORK_TOKENS[network]["pufETH"]["address"]
        
        # Create contract instance
        pufeth_contract = w3.eth.contract(
            address=w3.to_checksum_address(pufeth_address),
            abi=PUFETH_ABI
        )
        
        # Convert pufETH shares to underlying ETH assets
        eth_amount = pufeth_contract.functions.convertToAssets(int(pufeth_amount)).call()
        
        # ETH ≈ WETH (1:1 ratio)
        weth_amount = eth_amount
        
        # Calculate conversion rate
        pufeth_amount_decimal = Decimal(pufeth_amount)
        eth_amount_decimal = Decimal(eth_amount)
        rate = eth_amount_decimal / pufeth_amount_decimal if pufeth_amount_decimal > 0 else Decimal('0')
        
        return {
            "quote": {
                "quote": {
                    "buyAmount": str(int(weth_amount)),
                    "sellAmount": pufeth_amount,
                    "feeAmount": "0"
                }
            },
            "conversion_details": {
                "source": "Puffer pufETH.convertToAssets()",
                "price_impact": "0.0000",  # Native conversion has no price impact
                "rate": str(rate),
                "fee_percentage": "0.0000",
                "fallback": False,
                "note": f"Native pufETH conversion using convertToAssets() = {rate:.6f}",
                "eth_per_pufeth": str(eth_amount)
            }
        }
        
    except Exception as e:
        return {
            "quote": None,
            "conversion_details": {
                "source": "Error",
                "price_impact": "N/A",
                "rate": "0",
                "fee_percentage": "N/A",
                "fallback": True,
                "note": f"pufETH native conversion failed: {str(e)[:200]}"
            }
        }

def is_wsteth(token_address: str, network: str = "ethereum") -> bool:
    """
    Check if a token address is wstETH.
    
    Args:
        token_address: Token address to check
        network: Network to check on
        
    Returns:
        bool: True if token is wstETH
    """
    try:
        wsteth_address = NETWORK_TOKENS[network]["wstETH"]["address"]
        return token_address.lower() == wsteth_address.lower()
    except (KeyError, AttributeError):
        return False

def is_pufeth(token_address: str, network: str = "ethereum") -> bool:
    """
    Check if a token address is pufETH.
    
    Args:
        token_address: Token address to check
        network: Network to check on
        
    Returns:
        bool: True if token is pufETH
    """
    try:
        pufeth_address = NETWORK_TOKENS[network]["pufETH"]["address"]
        return token_address.lower() == pufeth_address.lower()
    except (KeyError, AttributeError):
        return False

def should_use_native_conversion(token_address: str, network: str = "ethereum", context: str = "spot") -> bool:
    """
    Check if native conversion should be used for a given token based on context.
    
    Args:
        token_address: Token address to check
        network: Network to check on
        context: Context of the conversion ("spot" or "euler")
        
    Returns:
        bool: True if native conversion should be used
    """
    # TEMPORARILY DISABLED: Force CowSwap for all conversions (liquidity pricing)
    # Native conversions are disabled to use only market-based liquidity pricing
    return False
    
    # ORIGINAL CODE (temporarily disabled):
    # # For Euler, always use market prices (CowSwap)
    # if context == "euler":
    #     return False
    # 
    # # For spot, use native conversion when available
    # if context == "spot" and ConversionConfig.should_use_native_for_spot():
    #     # Currently only pufETH uses native conversion for spot
    #     # wstETH support is available but disabled (can be re-enabled by uncommenting below)
    #     return is_pufeth(token_address, network)
    #     
    #     # Uncomment the line below to re-enable wstETH native conversion for spot:
    #     # return is_wsteth(token_address, network) or is_pufeth(token_address, network)
    # 
    # # Default: use CowSwap
    # return False 