from decimal import Decimal

class TokenConverter:
    def __init__(self, network, usdc_address):
        self.network = network
        self.usdc_address = usdc_address

    def convert_to_usdc(self, token: str, amount: str) -> tuple[str, dict]:
        """
        Converts token amount to USDC using CoW Protocol.
        """
        try:
            amount_decimal = Decimal(amount) / Decimal(10**18)
            print(f"  Converting {amount_decimal:.6f} {token} to USDC")
            
            quote = get_quote(
                network=self.network,
                sell_token=token,
                buy_token=self.usdc_address,
                amount=amount
            )
            
            if isinstance(quote, dict) and 'quote' in quote:
                usdc_amount = quote['quote']['buyAmount']
                usdc_normalized = Decimal(usdc_amount) / Decimal(10**6)
                
                print(f"  Quote received:")
                print(f"  → Output: {usdc_normalized:.6f} USDC")
                if quote['quote'].get('priceImpact'):
                    print(f"  → Price Impact: {quote['quote']['priceImpact']:.4f}%")
                
                return str(usdc_amount), {
                    "source": "CoWSwap",
                    "price_impact": quote['quote'].get('priceImpact', 'N/A'),
                    "rate": str(usdc_normalized / amount_decimal),
                    "fallback": False
                }
                
            print("  Using fallback price discovery...")
            return self._get_fallback_quote(token, amount)
            
        except Exception as e:
            print(f"  Error in conversion: {str(e)}")
            return self._get_fallback_quote(token, amount) 