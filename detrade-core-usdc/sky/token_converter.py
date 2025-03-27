from decimal import Decimal, ROUND_DOWN
from config.networks import NETWORK_TOKENS, RPC_URLS
from web3 import Web3
from cowswap.cow_client import get_quote

class TokenConverter:
    def __init__(self, network="base"):
        self.network = network
        self.w3 = Web3(Web3.HTTPProvider(RPC_URLS[network]))
        
        # Pour l'instant, on désactive l'initialisation des contrats PSM
        # jusqu'à ce qu'on ait la bonne configuration
        self.psm_contract = None

    def get_conversion_rate(self, usds_amount: str) -> str:
        """Get actual conversion rate from PSM contract"""
        # Pour l'instant, on retourne le même montant (ratio 1:1)
        return usds_amount

    def convert_usds_to_usdc(self, usds_amount: str) -> tuple[str, dict]:
        """
        Convert USDS to USDC using CoWSwap for accurate market price
        """
        try:
            # Get correct token addresses - toujours utiliser le token USDS sous-jacent
            sell_token = NETWORK_TOKENS[self.network]["sUSDS"]["underlying"]["USDS"]["address"]
            usdc_address = NETWORK_TOKENS[self.network]["USDC"]["address"]

            print(f"Converting USDS ({sell_token}) to USDC ({usdc_address}) on {self.network}")

            quote = get_quote(
                network=self.network,
                sell_token=sell_token,
                buy_token=usdc_address,
                amount=usds_amount
            )
            
            if isinstance(quote, dict) and 'quote' in quote:
                usdc_amount = quote['quote']['buyAmount']
                sell_amount = quote['quote']['sellAmount']
                fee_amount = quote['quote'].get('feeAmount', '0')
                
                # Calculate rate and price impact
                sell_normalized = Decimal(sell_amount) / Decimal(10**18)
                usdc_normalized = Decimal(usdc_amount) / Decimal(10**6)
                rate = usdc_normalized / sell_normalized if sell_normalized != 0 else Decimal('0')
                
                price_impact = ((rate - Decimal('1.0')) * Decimal('100'))
                fee_percentage = (Decimal(fee_amount) / Decimal(usds_amount)) * Decimal('100')
                
                return str(usdc_amount), {
                    "source": "CoWSwap",
                    "price_impact": f"{float(price_impact):.4f}%",
                    "rate": f"{float(rate):.6f}",
                    "fee_percentage": f"{float(fee_percentage):.4f}%",
                    "fallback": False
                }
            
            # Fallback to 1:1 conversion if quote fails
            print("CoWSwap quote failed, using fallback")
            return self._convert_decimals_18_to_6(usds_amount), {
                "source": "Fallback 1:1",
                "price_impact": "N/A",
                "rate": "1",
                "fallback": True
            }
            
        except Exception as e:
            print(f"Error in CoWSwap conversion: {str(e)}")
            return self._convert_decimals_18_to_6(usds_amount), {
                "source": "Error Fallback 1:1",
                "price_impact": "N/A",
                "rate": "1",
                "fallback": True
            }

    def _convert_decimals_18_to_6(self, amount_18_decimals: str) -> str:
        """Convert amount from 18 decimals to 6 decimals"""
        try:
            amount = Decimal(amount_18_decimals) / Decimal(10 ** 18)
            return str(int((amount * Decimal(10 ** 6)).quantize(Decimal('1.'), rounding=ROUND_DOWN)))
        except:
            return "0" 