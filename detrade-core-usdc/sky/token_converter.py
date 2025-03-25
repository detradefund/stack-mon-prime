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
        
        Returns:
            tuple[str, dict]: (USDC amount, conversion details)
        """
        try:
            # Si le montant est 0, pas besoin d'appeler CoWSwap
            if usds_amount == "0" or usds_amount == 0:
                return "0", {
                    "source": "No conversion needed",
                    "price_impact": "N/A",
                    "rate": "N/A",
                    "fallback": False
                }

            quote = get_quote(
                network=self.network,
                sell_token_symbol="USDS",
                buy_token_symbol="USDC",
                amount=usds_amount
            )
            
            if isinstance(quote, dict) and 'quote' in quote:
                usdc_amount = quote['quote']['buyAmount']
                sell_amount = quote['quote']['sellAmount']  # Montant après frais
                fee_amount = quote['quote'].get('feeAmount', '0')
                
                # Normalisation des montants
                usds_normalized = Decimal(sell_amount) / Decimal(10**18)  # Utiliser sellAmount au lieu de usds_amount
                usdc_normalized = Decimal(usdc_amount) / Decimal(10**6)
                rate = usdc_normalized / usds_normalized if usds_normalized != 0 else Decimal('0')
                
                # Calcul de l'impact prix incluant les frais
                price_impact = ((rate - Decimal('1.0')) * Decimal('100'))
                
                # Calcul du pourcentage de frais
                fee_percentage = (Decimal(fee_amount) / Decimal(usds_amount)) * Decimal('100')
                
                conversion_info = {
                    "source": "CoWSwap",
                    "price_impact": f"{float(price_impact):.4f}%",
                    "rate": f"{float(rate):.6f}",
                    "fee_percentage": f"{float(fee_percentage):.4f}%",
                    "fallback": False
                }
                
                if abs(price_impact) > 5:  # 5%
                    print(f"Warning: High price impact {float(price_impact):.2f}%")
                    usdc_amount = self._convert_decimals_18_to_6(usds_amount)
                    conversion_info["fallback"] = True
                    
                return str(usdc_amount), conversion_info
            
            # Fallback
            return self._convert_decimals_18_to_6(usds_amount), {
                "source": "Fallback 1:1",
                "price_impact": "N/A",
                "rate": "N/A",
                "fallback": True
            }
            
        except Exception as e:
            print(f"Error in CoWSwap conversion: {e}")
            return self._convert_decimals_18_to_6(usds_amount), {
                "source": "Fallback 1:1",
                "price_impact": "N/A",
                "rate": "N/A",
                "fallback": True
            }

    def _convert_decimals_18_to_6(self, amount_18_decimals: str) -> str:
        """Fallback conversion method (1:1 ratio)"""
        try:
            amount = Decimal(amount_18_decimals) / Decimal(10 ** 18)
            amount_6_decimals = str(int((amount * Decimal(10 ** 6)).quantize(Decimal('1.'), rounding=ROUND_DOWN)))
            return amount_6_decimals
        except Exception as e:
            print(f"Error converting decimals: {e}")
            return "0" 