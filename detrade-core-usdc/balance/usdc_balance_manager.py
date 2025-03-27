from web3 import Web3
import sys
from pathlib import Path
from typing import Dict, Any
from decimal import Decimal

# Add parent directory to PYTHONPATH
root_path = str(Path(__file__).parent.parent)
sys.path.append(root_path)

from config.networks import NETWORK_TOKENS, RPC_URLS
from config.base_client import BaseProtocolClient
from cowswap.cow_client import get_quote

class StablecoinBalanceManager(BaseProtocolClient):
    """Manages stablecoin spot balances across networks"""
    
    def __init__(self):
        # Initialize Web3 connections for each network
        self.connections = {
            "ethereum": Web3(Web3.HTTPProvider(RPC_URLS['ethereum'])),
            "base": Web3(Web3.HTTPProvider(RPC_URLS['base']))
        }
        
        # Initialize contracts for each network
        self.contracts = self._init_contracts()

    def _init_contracts(self) -> Dict[str, Any]:
        """Initialize contracts for all stablecoins"""
        contracts = {
            "usdc": {}, 
            "usr": {}, 
            "crvusd": {}, 
            "gho": {}, 
            "fxusd": {}
        }
        
        # Standard ERC20 ABI for balanceOf function
        abi = [
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function"
            }
        ]
        
        # Initialize USDC contracts
        for network, w3 in self.connections.items():
            usdc_address = NETWORK_TOKENS[network]["USDC"]["address"]
            contracts["usdc"][network] = w3.eth.contract(
                address=Web3.to_checksum_address(usdc_address),
                abi=abi
            )
        
        # Initialize USR contracts (on both Ethereum and Base)
        contracts["usr"]["base"] = self.connections["base"].eth.contract(
            address=Web3.to_checksum_address(NETWORK_TOKENS["base"]["PT-USR-24APR2025"]["underlying"]["USR"]["address"]),
            abi=abi
        )
        contracts["usr"]["ethereum"] = self.connections["ethereum"].eth.contract(
            address=Web3.to_checksum_address(NETWORK_TOKENS["ethereum"]["USR"]["address"]),
            abi=abi
        )

        # Initialize crvUSD contract (only on Ethereum)
        crvusd_address = NETWORK_TOKENS["ethereum"]["crvUSD"]["address"]
        contracts["crvusd"]["ethereum"] = self.connections["ethereum"].eth.contract(
            address=Web3.to_checksum_address(crvusd_address),
            abi=abi
        )

        # Initialize GHO contract (only on Ethereum)
        gho_address = NETWORK_TOKENS["ethereum"]["GHO"]["address"]
        contracts["gho"]["ethereum"] = self.connections["ethereum"].eth.contract(
            address=Web3.to_checksum_address(gho_address),
            abi=abi
        )

        # Initialize fxUSD contract (only on Ethereum)
        fxusd_address = NETWORK_TOKENS["ethereum"]["fxUSD"]["address"]
        contracts["fxusd"]["ethereum"] = self.connections["ethereum"].eth.contract(
            address=Web3.to_checksum_address(fxusd_address),
            abi=abi
        )
            
        return contracts

    def _get_usdc_value(self, network: str, token_symbol: str, amount: str) -> tuple[str, dict]:
        """
        Get USDC value for a given token amount using CoWSwap
        Returns (usdc_amount, conversion_details)
        """
        try:
            if token_symbol == "USDC":
                return amount, {
                    "source": "Direct",
                    "price_impact": "0",
                    "rate": "1",
                    "fallback": False
                }

            # Get token contract address
            if token_symbol == "USR":
                token_address = (
                    NETWORK_TOKENS["ethereum"]["USR"]["address"]
                    if network == "ethereum"
                    else NETWORK_TOKENS["base"]["PT-USR-24APR2025"]["underlying"]["USR"]["address"]
                )
            else:
                token_address = NETWORK_TOKENS["ethereum"][token_symbol]["address"]

            print(f"Converting {token_symbol} ({token_address}) to USDC on {network}")  # Debug log

            quote = get_quote(
                network=network,
                sell_token=token_address,  # Using contract address instead of symbol
                buy_token=NETWORK_TOKENS[network]["USDC"]["address"],  # USDC contract address
                amount=amount
            )
            
            if isinstance(quote, dict) and 'quote' in quote:
                usdc_amount = quote['quote']['buyAmount']
                sell_amount = quote['quote']['sellAmount']
                fee_amount = quote['quote'].get('feeAmount', '0')
                
                # Calculate rate and price impact
                sell_decimals = 18  # All our other stablecoins have 18 decimals
                sell_normalized = Decimal(sell_amount) / Decimal(10**sell_decimals)
                usdc_normalized = Decimal(usdc_amount) / Decimal(10**6)
                rate = usdc_normalized / sell_normalized if sell_normalized != 0 else Decimal('0')
                
                price_impact = ((rate - Decimal('1.0')) * Decimal('100'))
                fee_percentage = (Decimal(fee_amount) / Decimal(amount)) * Decimal('100')
                
                return str(usdc_amount), {
                    "source": "CoWSwap",
                    "price_impact": f"{float(price_impact):.4f}%",
                    "rate": f"{float(rate):.6f}",
                    "fee_percentage": f"{float(fee_percentage):.4f}%",
                    "fallback": False
                }
            
            # Si la quote échoue, on utilise le fallback
            print(f"CoWSwap quote failed for {token_symbol}, using fallback")  # Debug log
            return self._convert_to_usdc(amount), {
                "source": "Fallback 1:1",
                "price_impact": "N/A",
                "rate": "1",
                "fallback": True
            }
            
        except Exception as e:
            print(f"Error converting {token_symbol} to USDC: {str(e)}")  # Plus de détails dans l'erreur
            return self._convert_to_usdc(amount), {
                "source": "Error Fallback 1:1",
                "price_impact": "N/A",
                "rate": "1",
                "fallback": True
            }

    def _convert_to_usdc(self, amount_18_decimals: str) -> str:
        """Convert amount from 18 decimals to 6 decimals (USDC)"""
        try:
            amount = Decimal(amount_18_decimals) / Decimal(10 ** 18)
            return str(int((amount * Decimal(10 ** 6)).quantize(Decimal('1.'))))
        except:
            return "0"

    def get_balances(self, address: str) -> Dict[str, Any]:
        """Get stablecoin balances across all networks"""
        result = {
            "summary": {
                "total_stablecoins": "0",  # Total en nombre d'unités de stablecoins
                "total_usdc_value": "0",   # Total converti en USDC
                "networks": {}              # Résumé par réseau
            },
            "stablecoins": {}
        }
        
        try:
            checksum_address = Web3.to_checksum_address(address)
            total_stables = Decimal('0')
            total_usdc_value = Decimal('0')
            network_summaries = {}
            
            # Get all stablecoin balances
            for token_type, network_contracts in self.contracts.items():
                for network, contract in network_contracts.items():
                    if network not in network_summaries:
                        network_summaries[network] = {
                            "stablecoins": "0",
                            "usdc_value": "0"
                        }
                    
                    balance = contract.functions.balanceOf(checksum_address).call()
                    
                    if balance > 0:
                        if network not in result["stablecoins"]:
                            result["stablecoins"][network] = {}
                        
                        # Determine token symbol and data based on token type
                        if token_type == "usdc":
                            # Simplified structure for USDC
                            result["stablecoins"][network]["USDC"] = {
                                "amount": str(balance),
                                "decimals": NETWORK_TOKENS[network]["USDC"]["decimals"]
                            }
                            # Add to totals
                            usdc_normalized = Decimal(balance) / Decimal(10**6)
                            total_stables += usdc_normalized
                            total_usdc_value += usdc_normalized
                            network_summaries[network]["stablecoins"] = str(Decimal(network_summaries[network]["stablecoins"]) + usdc_normalized)
                            network_summaries[network]["usdc_value"] = str(Decimal(network_summaries[network]["usdc_value"]) + usdc_normalized)
                        else:
                            # For other tokens, keep the conversion logic
                            token_symbol = (
                                "USR" if token_type == "usr"
                                else "crvUSD" if token_type == "crvusd"
                                else "fxUSD" if token_type == "fxusd"
                                else token_type.upper()
                            )
                            token_data = (
                                NETWORK_TOKENS["ethereum"]["USR"] if token_type == "usr" and network == "ethereum"
                                else NETWORK_TOKENS["base"]["PT-USR-24APR2025"]["underlying"]["USR"] if token_type == "usr"
                                else NETWORK_TOKENS["ethereum"][token_symbol]
                            )

                            # Get USDC value
                            usdc_amount, conversion_details = self._get_usdc_value(
                                network=network,
                                token_symbol=token_symbol,
                                amount=str(balance)
                            )
                            
                            # Add to totals
                            token_normalized = Decimal(balance) / Decimal(10**token_data["decimals"])
                            usdc_normalized = Decimal(usdc_amount) / Decimal(10**6)
                            total_stables += token_normalized
                            total_usdc_value += usdc_normalized
                            network_summaries[network]["stablecoins"] = str(Decimal(network_summaries[network]["stablecoins"]) + token_normalized)
                            network_summaries[network]["usdc_value"] = str(Decimal(network_summaries[network]["usdc_value"]) + usdc_normalized)
                            
                            result["stablecoins"][network][token_symbol] = {
                                "amount": str(balance),
                                "decimals": token_data["decimals"],
                                "value": {
                                    "USDC": {
                                        "amount": usdc_amount,
                                        "decimals": 6,
                                        "conversion_details": conversion_details
                                    }
                                }
                            }
                
            # Update summary
            result["summary"].update({
                "total_stablecoins": f"{total_stables:.6f}",
                "total_usdc_value": f"{total_usdc_value:.6f}",
                "networks": network_summaries
            })
                
        except Exception as e:
            print(f"Error getting stablecoin balances: {str(e)}")
            
        return result

    def format_balance(self, balance: int, decimals: int) -> str:
        """Format raw balance to human readable format"""
        return str(Decimal(balance) / Decimal(10**decimals))

    def get_supported_networks(self) -> list:
        """Implementation of abstract method"""
        return list(self.connections.keys())
    
    def get_protocol_info(self) -> dict:
        """Implementation of abstract method"""
        return {
            "name": "Stablecoin Spot",
            "tokens": {
                "USDC": {
                    network: NETWORK_TOKENS[network]["USDC"]
                    for network in self.get_supported_networks()
                },
                "USR": {
                    "ethereum": NETWORK_TOKENS["ethereum"]["USR"],
                    "base": NETWORK_TOKENS["base"]["PT-USR-24APR2025"]["underlying"]["USR"]
                },
                "crvUSD": {
                    "ethereum": NETWORK_TOKENS["ethereum"]["crvUSD"]
                },
                "GHO": {
                    "ethereum": NETWORK_TOKENS["ethereum"]["GHO"]
                },
                "fxUSD": {
                    "ethereum": NETWORK_TOKENS["ethereum"]["fxUSD"]
                }
            }
        }

def main():
    import os
    from dotenv import load_dotenv
    import json
    
    # Load environment variables
    load_dotenv(Path(root_path) / '.env')
    
    # Get address from command line or .env
    test_address = sys.argv[1] if len(sys.argv) > 1 else os.getenv('DEFAULT_USER_ADDRESS')
    
    if not test_address:
        print("Error: No address provided and DEFAULT_USER_ADDRESS not found in .env")
        sys.exit(1)
    
    manager = StablecoinBalanceManager()
    
    print(f"\nFetching stablecoin balances for {test_address}")
    print("=" * 50)
    
    balances = manager.get_balances(test_address)
    
    print("\nRaw balances:")
    print(json.dumps(balances, indent=2))
    
    print("\nHuman readable balances:")
    for network, tokens in balances["stablecoins"].items():
        print(f"\n{network.upper()}:")
        for token_symbol, token_data in tokens.items():
            amount = int(token_data["amount"])
            decimals = token_data["decimals"]
            print(f"  {token_symbol}: {manager.format_balance(amount, decimals)} {token_symbol}")

if __name__ == "__main__":
    main() 