from decimal import Decimal, ROUND_DOWN
from config.networks import NETWORK_TOKENS, RPC_URLS
from web3 import Web3
from cowswap.cow_client import get_quote

"""
Sky Protocol token conversion module.
Handles USDS to USDC conversions with market-based pricing.
Uses CoW Protocol for accurate price discovery with fallback mechanisms.
"""

class TokenConverter:
    """
    Manages token conversions for Sky Protocol positions.
    Provides market-based pricing through CoW Protocol with fallback options.
    Handles decimal adjustments between different token standards.
    """
    
    def __init__(self, network="base"):
        # Initialize network connection
        self.network = network
        self.w3 = Web3(Web3.HTTPProvider(RPC_URLS[network]))
        
        # PSM contract initialization disabled pending configuration
        self.psm_contract = None

    def get_conversion_rate(self, usds_amount: str) -> str:
        """
        Gets conversion rate from PSM contract (currently stubbed).
        
        Note:
            Currently returns 1:1 ratio until PSM integration is complete
        """
        # Temporary 1:1 conversion until PSM implementation
        return usds_amount

    def convert_usds_to_usdc(self, usds_amount: str) -> tuple[str, dict]:
        """
        Converts USDS to USDC using market-based pricing.
        
        Args:
            usds_amount: Amount of USDS in wei (18 decimals)
            
        Returns:
            Tuple containing:
            - USDC amount in wei (6 decimals)
            - Conversion details including:
                - Price source
                - Price impact
                - Conversion rate
                - Fee information
                - Fallback status
                
        Note:
            Uses CoW Protocol for price discovery
            Includes fallback to 1:1 conversion if market pricing fails
        """
        try:
            # Get underlying USDS token address (not sUSDS)
            sell_token = NETWORK_TOKENS[self.network]["sUSDS"]["underlying"]["USDS"]["address"]
            usdc_address = NETWORK_TOKENS[self.network]["USDC"]["address"]

            quote = get_quote(
                network=self.network,
                sell_token=sell_token,
                buy_token=usdc_address,
                amount=usds_amount
            )
            
            if isinstance(quote, dict) and 'quote' in quote:
                # Process quote and return results without intermediate logs
                usdc_amount = quote['quote']['buyAmount']
                sell_amount = quote['quote']['sellAmount']
                fee_amount = quote['quote'].get('feeAmount', '0')
                
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
            
            # Fallback to 1:1 conversion if market quote fails
            print("  ⚠️ CoW Protocol quote failed, using fallback conversion")
            fallback_amount = self._convert_decimals_18_to_6(usds_amount)
            print(f"  → Using 1:1 conversion rate")
            print(f"  → Output: {Decimal(fallback_amount) / Decimal(10**6):.6f} USDC")
            
            return fallback_amount, {
                "source": "Fallback 1:1",
                "price_impact": "N/A",
                "rate": "1",
                "fallback": True
            }
            
        except Exception as e:
            print(f"  ❌ Error in conversion: {str(e)}")
            print("  → Falling back to 1:1 conversion")
            fallback_amount = self._convert_decimals_18_to_6(usds_amount)
            print(f"  → Output: {Decimal(fallback_amount) / Decimal(10**6):.6f} USDC")
            
            return fallback_amount, {
                "source": "Error Fallback 1:1",
                "price_impact": "N/A",
                "rate": "1",
                "fallback": True
            }

    def _convert_decimals_18_to_6(self, amount_18_decimals: str) -> str:
        """
        Converts amount from 18 decimals (USDS) to 6 decimals (USDC).
        Uses ROUND_DOWN for conservative value calculation.
        
        Args:
            amount_18_decimals: Amount in wei with 18 decimals
            
        Returns:
            Amount in wei with 6 decimals, rounded down
        """
        try:
            amount = Decimal(amount_18_decimals) / Decimal(10 ** 18)
            return str(int((amount * Decimal(10 ** 6)).quantize(Decimal('1.'), rounding=ROUND_DOWN)))
        except:
            return "0" 