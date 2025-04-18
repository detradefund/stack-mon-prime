import sys
from pathlib import Path
# Ajouter le répertoire parent au PYTHONPATH
sys.path.append(str(Path(__file__).parent.parent))

from web3 import Web3
from decimal import Decimal
from typing import Dict, Any
from dotenv import load_dotenv
from config.networks import RPC_URLS, NETWORK_TOKENS
from .abis import SUSDS_ABI
from cowswap.cow_client import get_quote
from config.base_client import BaseProtocolClient

"""
Sky Protocol balance manager module.
Provides high-level interface for fetching Sky Protocol positions and balances.
Handles direct interaction with Sky Protocol contracts and balance aggregation.
"""

# Load environment variables
load_dotenv()

class BalanceManager(BaseProtocolClient):
    """
    Manages Sky Protocol positions and balance fetching.
    Handles direct contract interactions and standardized balance reporting.
    """
    
    def __init__(self):
        # Initialize network-specific Web3 connections
        self.eth_w3 = Web3(Web3.HTTPProvider(RPC_URLS['ethereum']))
        self.base_w3 = Web3(Web3.HTTPProvider(RPC_URLS['base']))
        
        # Setup contract instances for each network
        self.eth_contract = self._init_eth_contract()
        self.base_contract = self._init_base_contract()

    def _init_eth_contract(self):
        """Initializes Ethereum sUSDS contract instance"""
        return self.eth_w3.eth.contract(
            address=NETWORK_TOKENS['ethereum']['sUSDS']['address'],
            abi=SUSDS_ABI
        )

    def _init_base_contract(self):
        """Initializes Base network sUSDS contract instance"""
        return self.base_w3.eth.contract(
            address=NETWORK_TOKENS['base']['sUSDS']['address'],
            abi=SUSDS_ABI
        )

    def _get_usdc_conversion(self, network: str, usds_amount: str) -> tuple[str, dict]:
        """Converts USDS to USDC using CoWSwap directly"""
        try:
            print("\nUSDC Conversion:")
            print(f"[Attempt 1/3] Requesting CoWSwap quote...")
            
            sell_token = NETWORK_TOKENS[network]["sUSDS"]["underlying"]["USDS"]["address"]
            usdc_address = NETWORK_TOKENS[network]["USDC"]["address"]

            quote = get_quote(
                network=network,
                sell_token=sell_token,
                buy_token=usdc_address,
                amount=usds_amount
            )
            
            if isinstance(quote, dict) and 'quote' in quote:
                usdc_amount = quote['quote']['buyAmount']
                sell_amount = quote['quote']['sellAmount']
                fee_amount = quote['quote'].get('feeAmount', '0')
                
                sell_normalized = Decimal(sell_amount) / Decimal(10**18)
                usdc_normalized = Decimal(usdc_amount) / Decimal(10**6)
                rate = usdc_normalized / sell_normalized if sell_normalized != 0 else Decimal('0')
                
                price_impact = ((rate - Decimal('1.0')) * Decimal('100'))
                fee_percentage = (Decimal(fee_amount) / Decimal(usds_amount)) * Decimal('100')
                
                print(f"✓ Direct quote successful:")
                print(f"  - Sell amount: {sell_normalized} USDS")
                print(f"  - Buy amount: {usdc_normalized} USDC")
                print(f"  - Rate: {float(rate):.6f} USDC/USDS")
                print(f"  - Fee: {float(fee_percentage):.4f}%")
                
                return str(usdc_amount), {
                    "source": "CoWSwap",
                    "price_impact": f"{float(price_impact):.4f}%",
                    "rate": f"{float(rate):.6f}",
                    "fee_percentage": f"{float(fee_percentage):.4f}%",
                    "fallback": False,
                    "note": "Direct CoWSwap quote"
                }
            
            # Si le montant est trop petit, utiliser le fallback silencieusement
            error_response = quote if isinstance(quote, str) else str(quote)
            if "SellAmountDoesNotCoverFee" in error_response:
                print("! Amount too small for direct quote, trying fallback method...")
                reference_amount = "1000000000000000000000"  # 1000 tokens
                
                print(f"Requesting quote with reference amount (1000 USDS)...")
                fallback_quote = get_quote(
                    network=network,
                    sell_token=sell_token,
                    buy_token=usdc_address,
                    amount=reference_amount
                )
                
                if isinstance(fallback_quote, dict) and 'quote' in fallback_quote:
                    sell_amount = Decimal(fallback_quote['quote']['sellAmount'])
                    buy_amount = Decimal(fallback_quote['quote']['buyAmount'])
                    
                    sell_normalized = sell_amount / Decimal(10**18)
                    buy_normalized = buy_amount / Decimal(10**6)
                    
                    rate = buy_normalized / sell_normalized
                    
                    original_amount_normalized = Decimal(usds_amount) / Decimal(10**18)
                    estimated_value = int(original_amount_normalized * rate * Decimal(10**6))
                    
                    print(f"✓ Fallback successful:")
                    print(f"  - Discovered rate: {float(rate):.6f} USDC/USDS")
                    print(f"  - Estimated value: {estimated_value/10**6:.6f} USDC")
                    
                    return str(estimated_value), {
                        "source": "CoWSwap-Fallback",
                        "price_impact": "0.0000%",
                        "rate": f"{float(rate):.6f}",
                        "fee_percentage": "N/A",
                        "fallback": True,
                        "note": "Using reference amount of 1000 tokens for price discovery due to small amount"
                    }
            
            print("! CoWSwap quote failed, using fallback conversion")
            fallback_amount = str(int(Decimal(usds_amount) / Decimal(10**12)))
            print(f"→ Using 1:1 conversion rate")
            print(f"→ Output: {int(fallback_amount)/10**6:.6f} USDC")
            
            return fallback_amount, {
                "source": "Fallback 1:1",
                "price_impact": "N/A",
                "rate": "1",
                "fee_percentage": "N/A",
                "fallback": True,
                "note": "Using 1:1 conversion rate as fallback after CoWSwap quote failed"
            }
            
        except Exception as e:
            print(f"✗ Error in conversion: {str(e)}")
            print("→ Falling back to 1:1 conversion")
            fallback_amount = str(int(Decimal(usds_amount) / Decimal(10**12)))
            print(f"→ Output: {int(fallback_amount)/10**6:.6f} USDC")
            
            return fallback_amount, {
                "source": "Error Fallback 1:1",
                "price_impact": "N/A",
                "rate": "1",
                "fee_percentage": "N/A",
                "fallback": True,
                "note": "Using 1:1 conversion rate due to technical error"
            }

    def _get_ethereum_position(self, address: str) -> dict:
        """Fetches and values Ethereum sUSDS position"""
        balance = self.eth_contract.functions.balanceOf(address).call()
        if balance == 0:
            return None
            
        staked = self.eth_contract.functions.balanceOf(address).call()
        usds_value = self.eth_contract.functions.convertToAssets(staked).call()
        
        return {
            "amount": str(staked),
            "decimals": NETWORK_TOKENS["ethereum"]["sUSDS"]["decimals"],
            "value": {
                "USDS": {
                    "amount": str(usds_value), 
                    "decimals": 18,
                    "conversion_details": {
                        "source": "Sky Protocol",
                        "price_impact": "0.0000%",
                        "rate": "1.000000",
                        "fee_percentage": "0.0000%",
                        "fallback": False,
                        "note": "Direct conversion using sUSDS.convertToAssets() function from Sky Protocol sUSDS contract"
                    }
                },
                "USDC": {
                    "amount": "0",  # Sera rempli plus tard
                    "decimals": 6,
                    "conversion_details": {}  # Sera rempli plus tard
                }
            }
        }

    def _get_base_position(self, address: str) -> dict:
        """Fetches and values Base network sUSDS position"""
        balance = self.base_contract.functions.balanceOf(address).call()
        if balance == 0:
            return None
        
        try:
            staked = self.base_contract.functions.balanceOf(address).call()
            # Utiliser le contrat Ethereum pour la conversion
            usds_value = self.eth_contract.functions.convertToAssets(staked).call()
            
            return {
                "amount": str(staked),
                "decimals": NETWORK_TOKENS["base"]["sUSDS"]["decimals"],
                "value": {
                    "USDS": {
                        "amount": str(usds_value), 
                        "decimals": 18,
                        "conversion_details": {
                            "source": "Sky Protocol (ETH)",
                            "price_impact": "0.0000%",
                            "rate": "1.000000",
                            "fee_percentage": "0.0000%",
                            "fallback": False,
                            "note": "Direct conversion using Ethereum sUSDS.convertToAssets() function"
                        }
                    },
                    "USDC": {
                        "amount": "0",  # Sera rempli plus tard
                        "decimals": 6,
                        "conversion_details": {}  # Sera rempli plus tard
                    }
                }
            }
        except Exception as e:
            print(f"Error in Base position conversion: {str(e)}")
            return {
                "amount": str(staked),
                "decimals": 18,
                "value": {
                    "USDS": {
                        "amount": str(staked),  # En cas d'erreur, on utilise le montant staké directement
                        "decimals": 18,
                        "conversion_details": {
                            "source": "Fallback",
                            "price_impact": "N/A",
                            "rate": "1",
                            "fee_percentage": "N/A",
                            "fallback": True,
                            "note": "Using 1:1 conversion due to error in ETH contract conversion"
                        }
                    },
                    "USDC": {
                        "amount": "0",
                        "decimals": 6,
                        "conversion_details": {}
                    }
                }
            }

    def _calculate_usdc_totals(self, positions: dict) -> dict:
        """Calculate USDC totals for a given set of positions"""
        total_wei = 0
        for token_data in positions.values():
            if "value" in token_data and "USDC" in token_data["value"]:
                total_wei += int(token_data["value"]["USDC"]["amount"])
        
        return {
            "total": {
                "wei": total_wei,
                "formatted": f"{total_wei / 1_000_000:.6f}"
            }
        }

    def get_balances(self, address: str = "0x0000000000000000000000000000000000000000") -> dict:
        """
        Retrieves all Sky Protocol positions for a given address.
        Returns data in a standardized format matching other protocols.
        """
        print("\n" + "="*80)
        print("SKY PROTOCOL BALANCE MANAGER")
        print("="*80)
        
        print("\nDebug get_balances:")
        print(f"Processing address: {address}")
        checksum_address = Web3.to_checksum_address(address)
        print(f"Checksum address: {checksum_address}")
        
        eth_position = self._get_ethereum_position(checksum_address)
        base_position = self._get_base_position(checksum_address)
        
        result = {"sky": {}}
        total_usdc_wei = 0

        print("\nProcessing network: ethereum")
        if eth_position:
            print("\nProcessing token: sUSDS")
            print(f"Amount: {eth_position['amount']} (decimals: {eth_position['decimals']})")
            print(f"Formatted amount: {(Decimal(eth_position['amount']) / Decimal(10**eth_position['decimals'])):.6f} sUSDS")
            print(f"Converted to USDS: {(Decimal(eth_position['value']['USDS']['amount']) / Decimal(10**18)):.6f} USDS")
            
            # USDC Conversion immédiatement après les infos du token
            usdc_value, conversion_info = self._get_usdc_conversion("ethereum", eth_position['value']['USDS']['amount'])
            eth_position['value']['USDC']['amount'] = usdc_value
            eth_position['value']['USDC']['conversion_details'] = conversion_info
            
            result["sky"]["ethereum"] = {"sUSDS": eth_position}
            chain_total = self._calculate_usdc_totals({"sUSDS": eth_position})
            result["sky"]["ethereum"]["usdc_totals"] = chain_total
            total_usdc_wei += chain_total["total"]["wei"]
        else:
            print("No position found")

        print("\nProcessing network: base")
        if base_position:
            print("\nProcessing token: sUSDS")
            print(f"Amount: {base_position['amount']} (decimals: {base_position['decimals']})")
            print(f"Formatted amount: {(Decimal(base_position['amount']) / Decimal(10**base_position['decimals'])):.6f} sUSDS")
            print(f"Converted to USDS: {(Decimal(base_position['value']['USDS']['amount']) / Decimal(10**18)):.6f} USDS")
            
            # USDC Conversion immédiatement après les infos du token
            usdc_value, conversion_info = self._get_usdc_conversion("base", base_position['value']['USDS']['amount'])
            base_position['value']['USDC']['amount'] = usdc_value
            base_position['value']['USDC']['conversion_details'] = conversion_info
            
            result["sky"]["base"] = {"sUSDS": base_position}
            chain_total = self._calculate_usdc_totals({"sUSDS": base_position})
            result["sky"]["base"]["usdc_totals"] = chain_total
            total_usdc_wei += chain_total["total"]["wei"]
        else:
            print("No position found")

        result["sky"]["usdc_totals"] = {
            "total": {
                "wei": total_usdc_wei,
                "formatted": f"{total_usdc_wei / 1_000_000:.6f}"
            }
        }
        
        print("\n" + "="*80)
        print(f"TOTAL SKY PROTOCOL VALUE: {total_usdc_wei / 1_000_000:.6f} USDC")
        print("="*80)
        
        return result

    def get_supported_networks(self) -> list:
        """Returns networks where Sky Protocol is deployed"""
        return ["ethereum", "base"]
    
    def get_protocol_info(self) -> dict:
        """Provides metadata about Sky Protocol integration"""
        return {
            "name": "Sky",
            "tokens": {
                "sUSDS": NETWORK_TOKENS["ethereum"]["sUSDS"]
            }
        }

def main():
    """CLI utility for testing Sky Protocol balance fetching"""
    import sys
    import json
    import os
    
    test_address = sys.argv[1] if len(sys.argv) > 1 else os.getenv('DEFAULT_USER_ADDRESS')
    
    if not test_address:
        print("Error: No address provided and DEFAULT_USER_ADDRESS not found in .env")
        sys.exit(1)
        
    manager = BalanceManager()
    balances = manager.get_balances(test_address)
    print(json.dumps(balances, indent=2))

if __name__ == "__main__":
    main() 