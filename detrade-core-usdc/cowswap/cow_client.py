import requests
from datetime import datetime, timezone
import sys
from pathlib import Path
import os
from dotenv import load_dotenv
import json

# Add parent directory to PYTHONPATH
sys.path.append(str(Path(__file__).parent.parent))

from config.networks import NETWORK_TOKENS  # Import correct

# Load environment variables
load_dotenv()
DEFAULT_USER_ADDRESS = os.getenv('DEFAULT_USER_ADDRESS')

def get_quote(network, sell_token, buy_token, amount):
    """Get raw quote from CoW Swap API"""
    api_network = "mainnet" if network == "ethereum" else network
    
    api_url = f"https://api.cow.fi/{api_network}/api/v1/quote"
    
    params = {
        "sellToken": sell_token,
        "buyToken": buy_token,
        "from": DEFAULT_USER_ADDRESS,
        "receiver": DEFAULT_USER_ADDRESS,
        "validTo": int(datetime.now(timezone.utc).timestamp() + 3600),
        "appData": "0x0000000000000000000000000000000000000000000000000000000000000000",
        "partiallyFillable": False,
        "sellTokenBalance": "erc20",
        "buyTokenBalance": "erc20",
        "kind": "sell",
        "sellAmountBeforeFee": str(amount)  # Conversion explicite en string
    }
    
    response = requests.post(api_url, json=params)
    return response.json() if response.ok else response.text

# Example usage
if __name__ == "__main__":
    # Test avec 10000 USDS
    amount = str(10000 * 10**18)  # 10000 USDS avec 18 décimales
    
    quote = get_quote(
        network="base",
        sell_token=NETWORK_TOKENS["base"]["USDS"]["address"],
        buy_token=NETWORK_TOKENS["base"]["USDC"]["address"],
        amount=amount
    )
    
    if isinstance(quote, dict) and 'quote' in quote:
        buy_amount = int(quote['quote']['buyAmount'])
        price_impact = float(quote['quote'].get('priceImpact', 0))
        
        print(f"\nTest conversion de 10000 USDS en USDC:")
        print(f"Input: 10000 USDS ({amount} wei)")
        print(f"Output: {buy_amount/10**6:.6f} USDC ({buy_amount} wei)")
        print(f"Price Impact: {price_impact*100:.2f}%")
    else:
        print(f"Error getting quote: {quote}") 