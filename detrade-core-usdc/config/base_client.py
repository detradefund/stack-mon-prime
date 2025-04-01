from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class TokenBalance:
    """
    Represents a token balance with its core properties.
    Used for standardizing token balance representation across protocols.
    """
    amount: int  # Raw token amount (including decimals)
    decimals: int  # Number of decimals for the token
    token: str  # Token identifier/address

@dataclass
class ProtocolPosition:
    """
    Represents a DeFi protocol position with its value in different tokens.
    Used for positions like LP tokens or staked assets.
    """
    raw_amount: int  # Raw position amount
    token: str  # Position token identifier
    values: Dict[str, int]  # Mapping of underlying token values (token -> amount)

class BaseProtocolClient(ABC):
    """
    Abstract base class defining the interface for protocol integrations.
    All protocol-specific clients must implement these methods to ensure
    consistent data fetching across the application.
    """
    
    @abstractmethod
    def get_balances(self, address: str) -> Dict[str, Any]:
        """
        Retrieves all protocol positions and their values for a given address.
        
        Args:
            address: The user's wallet address
            
        Returns:
            Dictionary containing position details and their valuations
        """
        pass
    
    @abstractmethod
    def get_supported_networks(self) -> list:
        """
        Lists all blockchain networks supported by this protocol integration.
        
        Returns:
            List of network identifiers (e.g., ['ethereum', 'arbitrum'])
        """
        pass
    
    @abstractmethod
    def get_protocol_info(self) -> dict:
        """
        Provides metadata about the protocol integration.
        
        Returns:
            Dictionary containing protocol information like name, type, and version
        """
        pass 