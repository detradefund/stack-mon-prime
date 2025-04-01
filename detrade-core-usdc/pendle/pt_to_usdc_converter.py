import requests
from typing import Dict, Optional, Tuple
from decimal import Decimal
from config.networks import NETWORK_TOKENS, CHAIN_IDS

"""
Pendle PT to USDC conversion module.
Handles price discovery and conversion quotes for Pendle Principal Tokens.
Uses Pendle's SDK API for accurate pricing with slippage and aggregator support.
"""

class PendleSwapClient:
    """
    Client for Pendle's swap API to price PT tokens in USDC.
    Handles price discovery with configurable slippage and aggregator settings.
    Includes price impact monitoring and safety checks.
    """
    
    API_CONFIG = {
        "base_url": "https://api-v2.pendle.finance/core/v1/sdk",
        "default_slippage": "1",  # 1% slippage tolerance
        "enable_aggregator": "true"  # Use aggregator for better pricing
    }

    MAX_PRICE_IMPACT = 0.05  # Maximum acceptable price impact (5%)
    
    def __init__(self):
        # Initialize configuration from network settings
        self.chain_ids = CHAIN_IDS
        self.default_slippage = self.API_CONFIG["default_slippage"]
        self.enable_aggregator = self.API_CONFIG["enable_aggregator"]

    def get_quote(self, 
                 network: str,
                 token_symbol: str,
                 amount_in_wei: str,
                 receiver: str = "0x0000000000000000000000000000000000000000") -> Tuple[int, float]:
        """
        Fetches quote for converting PT tokens to USDC using Pendle's SDK API.
        
        Args:
            network: Network identifier ('ethereum' or 'base')
            token_symbol: PT token symbol (e.g., 'PT-eUSDE-29MAY2025')
            amount_in_wei: Amount of PT tokens in wei (18 decimals)
            receiver: Address to receive USDC (default: zero address)
            
        Returns:
            Tuple containing:
            - USDC amount in wei (6 decimals)
            - Price impact as percentage
            
        Note:
            Includes price impact monitoring with 5% warning threshold
            Uses aggregator for optimal pricing when available
        """
        try:
            # Get token data and validate
            token_data = NETWORK_TOKENS[network][token_symbol]
            if token_data.get('protocol') != 'pendle':
                raise ValueError(f"Token {token_symbol} is not a Pendle token")

            # Get USDC address for network
            usdc_address = NETWORK_TOKENS[network]["USDC"]["address"]
            
            # Build API URL and parameters
            url = f"{self.API_CONFIG['base_url']}/{self.chain_ids[network]}/markets/{token_data['market']}/swap"
            params = {
                "receiver": receiver,
                "slippage": self.default_slippage,
                "enableAggregator": self.enable_aggregator,
                "tokenIn": token_data["address"],
                "tokenOut": usdc_address,
                "amountIn": amount_in_wei
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if 'data' not in data or 'amountOut' not in data['data']:
                raise ValueError("Invalid response from Pendle API")

            usdc_amount = int(data['data']['amountOut'])
            price_impact = float(data['data'].get('priceImpact', 0))
            
            if abs(price_impact) > self.MAX_PRICE_IMPACT * 100:
                print(f"  Warning: High price impact detected ({price_impact:.2f}%)")
            
            return usdc_amount, price_impact

        except Exception as e:
            raise Exception(f"Pendle quote failed: {str(e)}")

    def format_usdc_amount(self, wei_amount: int) -> Decimal:
        """
        Converts USDC amount from wei to human-readable format.
        
        Args:
            wei_amount: USDC amount in wei (6 decimals)
            
        Returns:
            Decimal representing USDC amount (e.g., 1000.123456)
        """
        return Decimal(wei_amount) / Decimal(10**6)

def main():
    """
    Test script for PendleSwapClient functionality.
    Tests quote fetching for 1 PT token on each supported network.
    """
    client = PendleSwapClient()
    
    # Test cases for different networks and tokens
    test_cases = [
        {
            "network": "ethereum",
            "token": "PT-eUSDE-29MAY2025",
            "amount": "1000000000000000000"  # 1 PT token
        },
        {
            "network": "base",
            "token": "PT-USR-24APR2025",
            "amount": "1000000000000000000"  # 1 PT token
        }
    ]
    
    for test in test_cases:
        print(f"\nTesting {test['token']} on {test['network']}:")
        try:
            usdc_amount, impact = client.get_quote(
                network=test['network'],
                token_symbol=test['token'],
                amount_in_wei=test['amount']
            )
            
            print(f"USDC Amount: {client.format_usdc_amount(usdc_amount):.6f} USDC")
            print(f"Price Impact: {impact:.6f}%")
            
        except Exception as e:
            print(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 