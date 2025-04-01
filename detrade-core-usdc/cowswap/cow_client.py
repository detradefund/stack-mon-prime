import requests
from datetime import datetime, timezone
import sys
from pathlib import Path
import os
from dotenv import load_dotenv
import json

"""
CoW Protocol (CoW Swap) API client.
Handles token price discovery and quote fetching for USDC conversions.
Used by balance managers to value non-USDC assets.
"""

# Add parent directory to PYTHONPATH
sys.path.append(str(Path(__file__).parent.parent))

from config.networks import NETWORK_TOKENS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DEFAULT_USER_ADDRESS = os.getenv('DEFAULT_USER_ADDRESS')

def get_quote(network: str, sell_token: str, buy_token: str, amount: str) -> dict:
    """
    Fetches price quote from CoW Protocol API for token conversion.
    
    Args:
        network: Network identifier ('ethereum' or 'base')
        sell_token: Address of token to sell
        buy_token: Address of token to buy (usually USDC)
        amount: Amount to sell in wei (as string)
    
    Returns:
        Quote data including:
        - Buy amount
        - Price impact
        - Fee estimates
        - Quote validity period
        
    Note:
        Uses 1-hour validity period for quotes
        Configured for ERC20-to-ERC20 swaps only
    """
    # Convert network name for API compatibility
    api_network = "mainnet" if network == "ethereum" else network
    
    api_url = f"https://api.cow.fi/{api_network}/api/v1/quote"
    
    # Prepare quote request parameters
    params = {
        "sellToken": sell_token,
        "buyToken": buy_token,
        "from": DEFAULT_USER_ADDRESS,
        "receiver": DEFAULT_USER_ADDRESS,
        "validTo": int(datetime.now(timezone.utc).timestamp() + 3600),  # 1 hour validity
        "appData": "0x0000000000000000000000000000000000000000000000000000000000000000",
        "partiallyFillable": False,
        "sellTokenBalance": "erc20",
        "buyTokenBalance": "erc20",
        "kind": "sell",
        "sellAmountBeforeFee": str(amount)  # Explicit string conversion for API
    }
    
    # Request quote from API
    response = requests.post(api_url, json=params)
    return response.json() if response.ok else response.text

if __name__ == "__main__":
    """
    Test script for CoW Protocol quote functionality.
    Attempts to get USDC quote for 10000 USDS.
    """
    # Test with 10000 USDS (18 decimals)
    amount = str(10000 * 10**18)
    
    quote = get_quote(
        network="base",
        sell_token=NETWORK_TOKENS["base"]["USDS"]["address"],
        buy_token=NETWORK_TOKENS["base"]["USDC"]["address"],
        amount=amount
    )
    
    if isinstance(quote, dict) and 'quote' in quote:
        buy_amount = int(quote['quote']['buyAmount'])
        price_impact = float(quote['quote'].get('priceImpact', 0))
        
        print("\nTest USDS to USDC conversion:")
        print(f"Input: 10000 USDS ({amount} wei)")
        print(f"Output: {buy_amount/10**6:.6f} USDC ({buy_amount} wei)")
        print(f"Price Impact: {price_impact*100:.2f}%")
    else:
        print(f"Error getting quote: {quote}") 