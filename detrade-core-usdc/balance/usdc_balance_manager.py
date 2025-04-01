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

class SpotBalanceManager(BaseProtocolClient):
    """Manages spot token balances across networks"""
    
    def __init__(self):
        # Initialize Web3 connections for each network
        self.connections = {
            "ethereum": Web3(Web3.HTTPProvider(RPC_URLS['ethereum'])),
            "base": Web3(Web3.HTTPProvider(RPC_URLS['base']))
        }
        
        # Initialize contracts for each network
        self.contracts = self._init_contracts()

    def _init_contracts(self) -> Dict[str, Any]:
        """Initialize contracts for all supported tokens"""
        contracts = {
            "usdc": {}, 
            "usr": {}, 
            "crvusd": {}, 
            "gho": {}, 
            "fxusd": {},
            "scrvusd": {},
            "cvx": {},  # Volatile token
            "crv": {}   # Volatile token
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

        # Initialize scrvUSD contract (only on Ethereum)
        scrvusd_address = NETWORK_TOKENS["ethereum"]["scrvUSD"]["address"]
        contracts["scrvusd"]["ethereum"] = self.connections["ethereum"].eth.contract(
            address=Web3.to_checksum_address(scrvusd_address),
            abi=abi
        )

        # Initialize CVX contract (only on Ethereum)
        cvx_address = NETWORK_TOKENS["ethereum"]["CVX"]["address"]
        contracts["cvx"]["ethereum"] = self.connections["ethereum"].eth.contract(
            address=Web3.to_checksum_address(cvx_address),
            abi=abi
        )

        # Initialize CRV contract (only on Ethereum)
        crv_address = NETWORK_TOKENS["ethereum"]["CRV"]["address"]
        contracts["crv"]["ethereum"] = self.connections["ethereum"].eth.contract(
            address=Web3.to_checksum_address(crv_address),
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

            # Get token contract address and decimals
            if token_symbol == "USR":
                token_address = (
                    NETWORK_TOKENS["ethereum"]["USR"]["address"]
                    if network == "ethereum"
                    else NETWORK_TOKENS["base"]["PT-USR-24APR2025"]["underlying"]["USR"]["address"]
                )
                token_decimals = (
                    NETWORK_TOKENS["ethereum"]["USR"]["decimals"]
                    if network == "ethereum"
                    else NETWORK_TOKENS["base"]["PT-USR-24APR2025"]["underlying"]["USR"]["decimals"]
                )
            else:
                token_address = NETWORK_TOKENS["ethereum"][token_symbol]["address"]
                token_decimals = NETWORK_TOKENS["ethereum"][token_symbol]["decimals"]

            # Try with original amount first
            quote = get_quote(
                network=network,
                sell_token=token_address,
                buy_token=NETWORK_TOKENS[network]["USDC"]["address"],
                amount=amount
            )

            if isinstance(quote, dict) and 'quote' in quote:
                usdc_amount = quote['quote']['buyAmount']
                sell_amount = quote['quote']['sellAmount']
                fee_amount = quote['quote'].get('feeAmount', '0')
                
                # Calculate rate and price impact
                sell_normalized = Decimal(sell_amount) / Decimal(10**token_decimals)
                usdc_normalized = Decimal(usdc_amount) / Decimal(10**6)
                rate = usdc_normalized / sell_normalized if sell_normalized != 0 else Decimal('0')
                
                price_impact = "N/A" if token_symbol in ["CVX", "CRV"] else f"{float((rate - Decimal('1.0')) * Decimal('100')):.4f}%"
                fee_percentage = (Decimal(fee_amount) / Decimal(amount)) * Decimal('100')
                
                return str(usdc_amount), {
                    "source": "CoWSwap",
                    "price_impact": price_impact,
                    "rate": f"{float(rate):.6f}",
                    "fee_percentage": f"{float(fee_percentage):.4f}%",
                    "fallback": False
                }

            # Si le montant est trop petit, utiliser le fallback silencieusement
            error_response = quote if isinstance(quote, str) else str(quote)
            if "SellAmountDoesNotCoverFee" in error_response:
                # Utiliser un montant plus grand pour obtenir un prix de référence
                reference_amount = "1000000000000000000000"  # 1000 tokens avec 18 decimals
                fallback_quote = get_quote(
                    network=network,
                    sell_token=token_address,
                    buy_token=NETWORK_TOKENS[network]["USDC"]["address"],
                    amount=reference_amount
                )
                
                if isinstance(fallback_quote, dict) and 'quote' in fallback_quote:
                    # Calculer le rate en utilisant les montants normalisés
                    sell_amount = Decimal(fallback_quote['quote']['sellAmount'])
                    buy_amount = Decimal(fallback_quote['quote']['buyAmount'])
                    
                    # Normaliser les montants (18 decimals -> 1 token, 6 decimals -> 1 USDC)
                    sell_normalized = sell_amount / Decimal(10**18)
                    buy_normalized = buy_amount / Decimal(10**6)
                    
                    # Calculer le rate (USDC par token)
                    rate = buy_normalized / sell_normalized
                    
                    # Appliquer le rate au montant original
                    original_amount_normalized = Decimal(amount) / Decimal(10**18)
                    estimated_value = int(original_amount_normalized * rate * Decimal(10**6))
                    
                    return str(estimated_value), {
                        "source": "CoWSwap-Fallback",
                        "price_impact": "0.0000%",
                        "rate": f"{float(rate):.6f}",
                        "fee_percentage": "N/A",
                        "fallback": True,
                        "fallback_reference": "1000 units"
                    }

            return "0", {
                "source": "Failed Quote",
                "price_impact": "N/A",
                "rate": "0",
                "fallback": True
            }

        except Exception as e:
            return "0", {
                "source": "Error",
                "price_impact": "N/A",
                "rate": "0",
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
        """Get spot token balances across all networks"""
        print("\n=== Processing Spot Balances ===")
        print(f"Checking spot token balances for {address}")
        
        result = {
            "summary": {
                "total_tokens": "0",
                "total_usdc_value": "0",
                "networks": {}
            },
            "stablecoins": {}
        }
        
        try:
            checksum_address = Web3.to_checksum_address(address)
            total_tokens = Decimal('0')
            total_usdc_value = Decimal('0')
            network_summaries = {}
            
            # Process each network
            for network in self.get_supported_networks():
                print(f"\n{network.upper()} Network:")
                network_found = False
                result["stablecoins"][network] = {}
                network_summaries[network] = {"tokens": "0", "usdc_value": "0"}
                
                # Process each token type
                for token_type, network_contracts in self.contracts.items():
                    if network not in network_contracts:
                        continue
                        
                    contract = network_contracts[network]
                    balance = contract.functions.balanceOf(checksum_address).call()
                    
                    if balance > 0:
                        network_found = True
                        token_symbol = token_type.upper()
                        if token_type == "crvusd":
                            token_symbol = "crvUSD"
                        elif token_type == "fxusd":
                            token_symbol = "fxUSD"
                        elif token_type == "scrvusd":
                            token_symbol = "scrvUSD"
                        
                        # Format and display balance
                        decimals = 6 if token_type == "usdc" else 18
                        balance_normalized = Decimal(balance) / Decimal(10**decimals)
                        print(f"- {token_symbol}:")
                        print(f"  Amount: {balance_normalized:.6f}")
                        
                        # Add to result
                        if token_type == "usdc":
                            result["stablecoins"][network][token_symbol] = {
                                "amount": str(balance),
                                "decimals": decimals
                            }
                            usdc_value = balance_normalized
                        else:
                            usdc_amount, conversion = self._get_usdc_value(network, token_symbol, str(balance))
                            usdc_normalized = Decimal(usdc_amount) / Decimal(10**6)
                            print(f"  USDC Value: {usdc_normalized:.6f}")
                            print(f"  Rate: {conversion['rate']}")
                            print(f"  Source: {conversion['source']}")
                            if conversion.get('price_impact') != "N/A":
                                print(f"  Price Impact: {conversion['price_impact']}")
                            
                            result["stablecoins"][network][token_symbol] = {
                                "amount": str(balance),
                                "decimals": decimals,
                                "value": {
                                    "USDC": {
                                        "amount": usdc_amount,
                                        "decimals": 6,
                                        "conversion_details": conversion
                                    }
                                }
                            }
                            usdc_value = usdc_normalized
                        
                        # Update totals
                        total_tokens += balance_normalized
                        total_usdc_value += usdc_value
                        network_summaries[network]["tokens"] = str(Decimal(network_summaries[network]["tokens"]) + balance_normalized)
                        network_summaries[network]["usdc_value"] = str(Decimal(network_summaries[network]["usdc_value"]) + usdc_value)
                
                if not network_found:
                    print("No balances found")
            
            # Update summary
            result["summary"].update({
                "total_tokens": f"{total_tokens:.6f}",
                "total_usdc_value": f"{total_usdc_value:.6f}",
                "networks": network_summaries
            })
            
        except Exception as e:
            print(f"Error getting spot token balances: {str(e)}")
        
        print("=== Spot Balances processing complete ===\n")
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
            "name": "Spot Tokens",
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
                },
                "scrvUSD": {
                    "ethereum": NETWORK_TOKENS["ethereum"]["scrvUSD"]
                },
                "CVX": {
                    "ethereum": NETWORK_TOKENS["ethereum"]["CVX"]
                },
                "CRV": {
                    "ethereum": NETWORK_TOKENS["ethereum"]["CRV"]
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
    
    manager = SpotBalanceManager()
    
    print(f"\nFetching spot token balances for {test_address}")
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