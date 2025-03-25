import requests
from typing import Dict, Optional, Tuple
from decimal import Decimal
from config.networks import NETWORK_TOKENS, CHAIN_IDS

class PendleSwapClient:
    """Client for Pendle PT to USDC price quotes"""
    
    API_CONFIG = {
        "base_url": "https://api-v2.pendle.finance/core/v1/sdk",
        "default_slippage": "1",
        "enable_aggregator": "true"
    }

    MAX_PRICE_IMPACT = 0.05  # 5%
    
    def __init__(self):
        self.chain_ids = CHAIN_IDS
        self.default_slippage = self.API_CONFIG["default_slippage"]
        self.enable_aggregator = self.API_CONFIG["enable_aggregator"]

    def get_quote(self, 
                 network: str,
                 token_symbol: str,
                 amount_in_wei: str,
                 receiver: str = "0x0000000000000000000000000000000000000000") -> Tuple[int, float]:
        """
        Get quote for swapping PT tokens to USDC
        
        Args:
            network: Network name (ethereum/base)
            token_symbol: Symbol of PT token (e.g. 'PT-eUSDE-29MAY2025', 'PT-USR-24APR2025')
            amount_in_wei: Amount of PT tokens in wei
            receiver: Address that would receive the USDC
            
        Returns:
            Tuple[int, float]: (USDC amount in wei, price impact)
        """
        try:
            # Get token data
            token_data = NETWORK_TOKENS[network][token_symbol]
            if token_data.get('protocol') != 'pendle':
                raise ValueError(f"Token {token_symbol} is not a Pendle token")

            # Get USDC address for the network
            usdc_address = NETWORK_TOKENS[network]["USDC"]["address"]
            
            # Build API URL
            url = f"{self.API_CONFIG['base_url']}/{self.chain_ids[network]}/markets/{token_data['market']}/swap"
            
            # Build parameters
            params = {
                "receiver": receiver,
                "slippage": self.default_slippage,
                "enableAggregator": self.enable_aggregator,
                "tokenIn": token_data["address"],
                "tokenOut": usdc_address,
                "amountIn": amount_in_wei
            }
            
            # Make API call
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if 'data' not in data or 'amountOut' not in data['data']:
                raise ValueError("Invalid response from Pendle API")

            usdc_amount = int(data['data']['amountOut'])
            price_impact = float(data['data'].get('priceImpact', 0))
            
            # Check price impact
            if abs(price_impact) > self.MAX_PRICE_IMPACT * 100:  # Convert to percentage
                print(f"Warning: High price impact {price_impact:.2f}%")
            
            return usdc_amount, price_impact

        except Exception as e:
            print(f"Error getting Pendle swap quote: {str(e)}")
            return 0, 0.0

    def format_usdc_amount(self, wei_amount: int) -> Decimal:
        """Convert USDC wei amount to decimal"""
        return Decimal(wei_amount) / Decimal(10**6)

def main():
    # Test the client
    client = PendleSwapClient()
    
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