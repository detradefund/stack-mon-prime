from typing import Dict, Any
from web3 import Web3
from config.networks import RPC_URLS, NETWORK_TOKENS
from .abis import SUSDS_ABI
from .token_converter import TokenConverter
from config.base_client import BaseProtocolClient

"""
Sky Protocol client implementation.
Handles interaction with Sky Protocol's sUSDS (Savings USDS) contracts.
Provides balance fetching and value conversion across networks.
"""

class SkyClient(BaseProtocolClient):
    """
    Core client for Sky Protocol contract interactions.
    Implements BaseProtocolClient interface for standardized protocol integration.
    Manages sUSDS positions on Ethereum and Base networks with USDC value conversion.
    """
    
    def __init__(self):
        # Initialize network-specific Web3 connections
        self.eth_w3 = Web3(Web3.HTTPProvider(RPC_URLS['ethereum']))
        self.base_w3 = Web3(Web3.HTTPProvider(RPC_URLS['base']))
        
        # Setup contract instances for each network
        self.eth_contract = self._init_eth_contract()
        self.base_contract = self._init_base_contract()
        
        # Initialize token converters for USDC value calculation
        self.eth_converter = TokenConverter("ethereum")
        self.base_converter = TokenConverter("base")

    def _init_eth_contract(self):
        """Initializes Ethereum sUSDS contract instance"""
        return self.eth_w3.eth.contract(
            address=NETWORK_TOKENS['ethereum']['sUSDS']['address'],
            abi=SUSDS_ABI
        )

    def _init_base_contract(self):
        """Initializes Base network sUSDS contract instance"""
        return self.base_w3.eth.contract(
            address=NETWORK_TOKENS['base']['sUSDS']['address'],
            abi=SUSDS_ABI
        )

    def get_positions(self, address: str) -> dict:
        """
        Retrieves sUSDS positions across all supported networks.
        
        Args:
            address: Wallet address to check
            
        Returns:
            Dict containing positions by network:
            {
                "sky": {
                    "ethereum": {"sUSDS": {...}},
                    "base": {"sUSDS": {...}}
                }
            }
        """
        eth_position = self._get_ethereum_position(address)
        base_position = self._get_base_position(address)
        
        result = {"sky": {}}
        
        # Only include networks with non-zero positions
        if eth_position is not None:
            result["sky"]["ethereum"] = {"sUSDS": eth_position}
        if base_position is not None:
            result["sky"]["base"] = {"sUSDS": base_position}
            
        return result

    def _get_ethereum_position(self, address: str) -> dict:
        """
        Fetches and values Ethereum sUSDS position.
        Includes conversion to both USDS and USDC values.
        
        Returns None if no position exists.
        """
        balance = self.eth_contract.functions.balanceOf(address).call()
        if balance == 0:
            return None
            
        checksum_address = Web3.to_checksum_address(address)
        staked = self.eth_contract.functions.balanceOf(checksum_address).call()
        usds_value = self.eth_contract.functions.convertToAssets(staked).call()
        usdc_value, conversion_info = self.eth_converter.convert_usds_to_usdc(usds_value)
        
        return {
            "amount": str(staked),
            "decimals": NETWORK_TOKENS["ethereum"]["sUSDS"]["decimals"],
            "value": {
                "USDS": {"amount": str(usds_value), "decimals": 18},
                "USDC": {
                    "amount": str(usdc_value),
                    "decimals": 6,
                    "conversion_details": conversion_info
                }
            }
        }

    def _get_base_position(self, address: str) -> dict:
        """
        Fetches and values Base network sUSDS position.
        Uses Ethereum contract for value conversion due to Base limitations.
        
        Returns None if no position exists.
        Includes error handling with safe fallback values.
        """
        balance = self.base_contract.functions.balanceOf(address).call()
        if balance == 0:
            return None
            
        try:
            checksum_address = Web3.to_checksum_address(address)
            staked = self.base_contract.functions.balanceOf(checksum_address).call()
            
            # Use Ethereum contract for USDS conversion
            usds_value = self.eth_contract.functions.convertToAssets(staked).call()
            usdc_value, conversion_info = self.base_converter.convert_usds_to_usdc(str(usds_value))
            
            return {
                "amount": str(staked),
                "decimals": NETWORK_TOKENS["base"]["sUSDS"]["decimals"],
                "value": {
                    "USDS": {"amount": str(usds_value), "decimals": 18},
                    "USDC": {
                        "amount": str(usdc_value),
                        "decimals": 6,
                        "conversion_details": conversion_info
                    }
                }
            }
        except Exception as e:
            print(f"Error in _get_base_position: {e}")
            # Return safe fallback values for error case
            return {
                "amount": "0",
                "decimals": 18,
                "value": {
                    "USDS": {"amount": "0", "decimals": 18},
                    "USDC": {
                        "amount": "0",
                        "decimals": 6,
                        "conversion_details": {
                            "source": "Error",
                            "price_impact": "N/A",
                            "rate": "0",
                            "fallback": True
                        }
                    }
                }
            }

    def get_balances(self, address: str) -> Dict[str, Any]:
        """
        Implementation of BaseProtocolClient.get_balances.
        Wraps get_positions for interface compatibility.
        """
        return self.get_positions(address)
    
    def get_supported_networks(self) -> list:
        """
        Implementation of BaseProtocolClient.get_supported_networks.
        Returns networks where Sky Protocol is deployed.
        """
        return ["ethereum", "base"]
    
    def get_protocol_info(self) -> dict:
        """
        Implementation of BaseProtocolClient.get_protocol_info.
        Provides metadata about Sky Protocol integration.
        """
        return {
            "name": "Sky",
            "tokens": {
                "sUSDS": NETWORK_TOKENS["ethereum"]["sUSDS"]
            }
        } 