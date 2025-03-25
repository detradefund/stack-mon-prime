from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class TokenBalance:
    amount: int
    decimals: int
    token: str

@dataclass
class ProtocolPosition:
    raw_amount: int
    token: str
    values: Dict[str, int]  # Token -> amount mapping

class BaseProtocolClient(ABC):
    """Abstract interface for all protocols"""
    
    @abstractmethod
    def get_balances(self, address: str) -> Dict[str, Any]:
        """Get balances for an address"""
        pass
    
    @abstractmethod
    def get_supported_networks(self) -> list:
        """List of networks supported by this protocol"""
        pass
    
    @abstractmethod
    def get_protocol_info(self) -> dict:
        """Protocol information"""
        pass 