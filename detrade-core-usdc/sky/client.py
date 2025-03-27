from typing import Dict, Any
from web3 import Web3
from config.networks import RPC_URLS, NETWORK_TOKENS
from .abis import SUSDS_ABI
from .token_converter import TokenConverter
from config.base_client import BaseProtocolClient

class SkyClient(BaseProtocolClient):
    def __init__(self):
        self.eth_w3 = Web3(Web3.HTTPProvider(RPC_URLS['ethereum']))
        self.base_w3 = Web3(Web3.HTTPProvider(RPC_URLS['base']))
        self.eth_contract = self._init_eth_contract()
        self.base_contract = self._init_base_contract()
        self.eth_converter = TokenConverter("ethereum")
        self.base_converter = TokenConverter("base")

    def _init_eth_contract(self):
        return self.eth_w3.eth.contract(
            address=NETWORK_TOKENS['ethereum']['sUSDS']['address'],
            abi=SUSDS_ABI
        )

    def _init_base_contract(self):
        return self.base_w3.eth.contract(
            address=NETWORK_TOKENS['base']['sUSDS']['address'],
            abi=SUSDS_ABI
        )

    def get_positions(self, address: str) -> dict:
        eth_position = self._get_ethereum_position(address)
        base_position = self._get_base_position(address)
        
        result = {"sky": {}}
        
        # N'ajouter le réseau que si la position existe
        if eth_position is not None:
            result["sky"]["ethereum"] = {"sUSDS": eth_position}
        if base_position is not None:
            result["sky"]["base"] = {"sUSDS": base_position}
            
        return result

    def _get_ethereum_position(self, address: str) -> dict:
        balance = self.eth_contract.functions.balanceOf(address).call()
        if balance == 0:  # Si balance est 0, retourner None au lieu d'un dict vide
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
        balance = self.base_contract.functions.balanceOf(address).call()
        if balance == 0:  # Si balance est 0, retourner None au lieu d'un dict vide
            return None
            
        try:
            checksum_address = Web3.to_checksum_address(address)
            staked = self.base_contract.functions.balanceOf(checksum_address).call()
            
            # On utilise le contrat Ethereum sUSDS pour convertir le montant
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
            # Return empty values in case of error
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
        """Implementation of abstract method"""
        return self.get_positions(address)
    
    def get_supported_networks(self) -> list:
        """Implementation of abstract method"""
        return ["ethereum", "base"]
    
    def get_protocol_info(self) -> dict:
        """Implementation of abstract method"""
        return {
            "name": "Sky",
            "tokens": {
                "sUSDS": NETWORK_TOKENS["ethereum"]["sUSDS"]
            }
        } 