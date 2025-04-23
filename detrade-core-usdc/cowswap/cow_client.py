import requests
from datetime import datetime, timezone
import sys
from pathlib import Path
import os
from dotenv import load_dotenv
import json
from decimal import Decimal
import time

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

def get_quote(network: str, sell_token: str, buy_token: str, amount: str, token_decimals: int = 18, token_symbol: str = "") -> dict:
    """
    Fetches price quote from CoW Protocol API for token conversion with fallback mechanism.
    
    Args:
        network: Network identifier ('ethereum' or 'base')
        sell_token: Address of token to sell
        buy_token: Address of token to buy (usually USDC)
        amount: Amount to sell in wei (as string)
        token_decimals: Decimals of the sell token (default 18)
        token_symbol: Symbol of the sell token (default "")
    
    Returns:
        Dict containing:
        - quote: API response with buy amount, etc.
        - conversion_details: Information about the conversion method used
    """
    retry_delays = [3, 5]  # Delays in seconds between retries
    api_network = "mainnet" if network == "ethereum" else network
    api_url = f"https://api.cow.fi/{api_network}/api/v1/quote"

    def make_request(params):
        response = requests.post(api_url, json=params)
        return response.json() if response.ok else response.text

    base_params = {
        "sellToken": sell_token,
        "buyToken": buy_token,
        "from": DEFAULT_USER_ADDRESS,
        "receiver": DEFAULT_USER_ADDRESS,
        "validTo": int(datetime.now(timezone.utc).timestamp() + 3600),  # 1 hour validity
        "appData": "0x0000000000000000000000000000000000000000000000000000000000000000",
        "partiallyFillable": False,
        "sellTokenBalance": "erc20",
        "buyTokenBalance": "erc20",
        "kind": "sell"
    }

    # Direct 1:1 conversion for USDC
    if token_symbol == "USDC":
        print("✓ Direct 1:1 conversion with USDC")
        return {
            "quote": {
                "quote": {
                    "buyAmount": amount,
                    "sellAmount": amount,
                    "feeAmount": "0"
                }
            },
            "conversion_details": {
                "source": "Direct",
                "price_impact": "0",
                "rate": "1",
                "fee_percentage": "0.0000%",
                "fallback": False,
                "note": "Direct 1:1 conversion"
            }
        }

    # Try direct quote first
    print(f"\nAttempting to get quote...")
    print(f"[Attempt 1/3] Requesting CoWSwap quote...")
    
    params = {**base_params, "sellAmountBeforeFee": str(amount)}
    quote = make_request(params)

    # If successful, return with direct quote details
    if isinstance(quote, dict) and 'quote' in quote:
        usdc_amount = int(quote['quote']['buyAmount'])
        rate = Decimal(quote['quote']['buyAmount']) / (Decimal(quote['quote']['sellAmount']) / Decimal(10**12))
        
        print("✓ Converted to USDC: {:.6f} USDC".format(usdc_amount/1e6))
        print(f"  Rate: {rate} USDC/token")
        print(f"  Source: CoWSwap")
        print(f"  Note: Direct CoWSwap quote")
        
        return {
            "quote": quote,
            "conversion_details": {
                "source": "CoWSwap",
                "price_impact": quote['quote'].get('priceImpact', '0'),
                "rate": str(rate),
                "fee_percentage": str(Decimal(quote['quote'].get('feeAmount', '0')) / Decimal(amount) * 100),
                "fallback": False,
                "note": "Direct CoWSwap quote"
            }
        }

    # If amount too small, try fallback with reference amount
    if isinstance(quote, str) and "SellAmountDoesNotCoverFee" in quote:
        print("! Amount too small for direct quote, trying fallback method...")
        print("Requesting quote with reference amount (1000 tokens)...")
        
        # Use 1000 tokens as reference
        reference_amount = str(1000 * 10**token_decimals)
        params = {**base_params, "sellAmountBeforeFee": reference_amount}
        fallback_quote = make_request(params)

        if isinstance(fallback_quote, dict) and 'quote' in fallback_quote:
            # Calculate rate using reference quote
            sell_amount = Decimal(fallback_quote['quote']['sellAmount'])
            buy_amount = Decimal(fallback_quote['quote']['buyAmount'])
            
            sell_normalized = sell_amount / Decimal(10**token_decimals)
            buy_normalized = buy_amount / Decimal(10**6)  # USDC has 6 decimals
            
            rate = buy_normalized / sell_normalized
            
            # Apply rate to original amount
            original_amount_normalized = Decimal(amount) / Decimal(10**token_decimals)
            estimated_value = int(original_amount_normalized * rate * Decimal(10**6))

            print("✓ Fallback successful:")
            print(f"  - Discovered rate: {rate:.6f} USDC/token")
            print(f"  - Estimated value: {estimated_value/1e6:.6f} USDC")

            return {
                "quote": {
                    "quote": {
                        "buyAmount": str(estimated_value),
                        "sellAmount": amount,
                        "feeAmount": "0"
                    }
                },
                "conversion_details": {
                    "source": "CoWSwap-Fallback",
                    "price_impact": "N/A",
                    "rate": f"{float(rate):.6f}",
                    "fee_percentage": "N/A",
                    "fallback": True,
                    "note": "Using reference amount of 1000 tokens for price discovery"
                }
            }

    # For other errors, retry with delays
    for attempt, delay in enumerate(retry_delays, 2):
        print(f"! Error on attempt {attempt-1}, retrying in {delay} seconds...")
        time.sleep(delay)
        print(f"[Attempt {attempt}/3] Requesting CoWSwap quote...")
        
        quote = make_request(params)
        
        if isinstance(quote, dict) and 'quote' in quote:
            return {
                "quote": quote,
                "conversion_details": {
                    "source": "CoWSwap",
                    "price_impact": quote['quote'].get('priceImpact', '0'),
                    "rate": str(Decimal(quote['quote']['buyAmount']) / (Decimal(quote['quote']['sellAmount']) / Decimal(10**12))),
                    "fee_percentage": str(Decimal(quote['quote'].get('feeAmount', '0')) / Decimal(amount) * 100),
                    "fallback": False,
                    "note": f"Direct quote after {attempt} attempts"
                }
            }

    # If all attempts fail
    return {
        "quote": None,
        "conversion_details": {
            "source": "Failed",
            "price_impact": "N/A",
            "rate": "0",
            "fee_percentage": "N/A",
            "fallback": True,
            "note": "All quote attempts failed"
        }
    }

if __name__ == "__main__":
    """
    Test script for CoW Protocol quote functionality.
    Attempts to get USDC quote for 10000 USDS.
    """
    # Test with 10000 USDS (18 decimals)
    amount = str(10000 * 10**18)
    
    result = get_quote(
        network="base",
        sell_token=NETWORK_TOKENS["base"]["USDS"]["address"],
        buy_token=NETWORK_TOKENS["base"]["USDC"]["address"],
        amount=amount
    )
    
    if result["quote"] and 'quote' in result["quote"]:
        quote = result["quote"]["quote"]
        buy_amount = int(quote['buyAmount'])
        
        print("\nTest USDS to USDC conversion:")
        print(f"Input: 10000 USDS ({amount} wei)")
        print(f"Output: {buy_amount/10**6:.6f} USDC ({buy_amount} wei)")
        print("Conversion details:", json.dumps(result["conversion_details"], indent=2))
    else:
        print(f"Error getting quote: {result}") 