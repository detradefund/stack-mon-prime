from web3 import Web3
import sys
from pathlib import Path
from typing import Dict, Any
from decimal import Decimal
import time

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
        Get USDC value for a given token amount using CoWSwap with retry mechanism
        Returns (usdc_amount, conversion_details)
        """
        retry_delays = [1, 3, 3]  # Delays in seconds between retries
        
        try:
            if token_symbol == "USDC":
                return amount, {
                    "source": "Direct",
                    "price_impact": "0",
                    "rate": "1",
                    "fee_percentage": "0.0000%",
                    "fallback": False,
                    "note": "Direct 1:1 conversion"
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

            for attempt, delay in enumerate(retry_delays, 1):
                try:
                    # Try direct quote first
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
                            "fallback": False,
                            "note": "Direct CoWSwap quote"
                        }

                    # Handle small amounts with fallback
                    error_response = quote if isinstance(quote, str) else str(quote)
                    if "SellAmountDoesNotCoverFee" in error_response:
                        # Use larger amount for price discovery
                        reference_amount = "1000000000000000000000"  # 1000 tokens with 18 decimals
                        fallback_quote = get_quote(
                            network=network,
                            sell_token=token_address,
                            buy_token=NETWORK_TOKENS[network]["USDC"]["address"],
                            amount=reference_amount
                        )
                        
                        if isinstance(fallback_quote, dict) and 'quote' in fallback_quote:
                            # Calculate rate using normalized amounts
                            sell_amount = Decimal(fallback_quote['quote']['sellAmount'])
                            buy_amount = Decimal(fallback_quote['quote']['buyAmount'])
                            
                            sell_normalized = sell_amount / Decimal(10**token_decimals)
                            buy_normalized = buy_amount / Decimal(10**6)
                            
                            rate = buy_normalized / sell_normalized
                            
                            # Apply rate to original amount
                            original_amount_normalized = Decimal(amount) / Decimal(10**token_decimals)
                            estimated_value = int(original_amount_normalized * rate * Decimal(10**6))
                            
                            return str(estimated_value), {
                                "source": "CoWSwap-Fallback",
                                "price_impact": "0.0000%",
                                "rate": f"{float(rate):.6f}",
                                "fee_percentage": "N/A",
                                "fallback": True,
                                "note": "Using reference amount of 1000 tokens for price discovery due to small amount"
                            }

                    if attempt < len(retry_delays):
                        time.sleep(delay)
                        continue

                except Exception as e:
                    if attempt < len(retry_delays):
                        time.sleep(delay)
                        continue

            return "0", {
                "source": "Failed",
                "price_impact": "N/A",
                "rate": "0",
                "fee_percentage": "N/A",
                "fallback": True,
                "note": "All quote attempts failed"
            }

        except Exception as e:
            return "0", {
                "source": "Error",
                "price_impact": "N/A",
                "rate": "0",
                "fee_percentage": "N/A",
                "fallback": True,
                "note": f"Technical error: {str(e)[:200]}"
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
        print("\n" + "="*80)
        print("SPOT BALANCE MANAGER")
        print("="*80)
        
        print("\nDebug get_balances:")
        print(f"Processing address: {address}")
        checksum_address = Web3.to_checksum_address(address)
        print(f"Checksum address: {checksum_address}")
        
        result = {
            "usdc_totals": {
                "total": {
                    "wei": 0,
                    "formatted": "0.00"
                }
            }
        }
        
        try:
            total_usdc_value = Decimal('0')
            
            # Process each network
            for network in self.get_supported_networks():
                print(f"\nProcessing network: {network}")
                network_has_balance = False
                network_balances = {}
                
                # Process each token type
                for token_type, network_contracts in self.contracts.items():
                    if network not in network_contracts:
                        continue
                        
                    contract = network_contracts[network]
                    balance = contract.functions.balanceOf(checksum_address).call()
                    
                    if balance > 0:
                        network_has_balance = True
                        token_symbol = token_type.upper()
                        if token_type == "crvusd":
                            token_symbol = "crvUSD"
                        elif token_type == "fxusd":
                            token_symbol = "fxUSD"
                        elif token_type == "scrvusd":
                            token_symbol = "scrvUSD"
                        
                        # Format balance
                        decimals = 6 if token_type == "usdc" else 18
                        balance_normalized = Decimal(balance) / Decimal(10**decimals)
                        
                        print(f"\nProcessing token: {token_symbol}")
                        print(f"Amount: {balance} (decimals: {decimals})")
                        print(f"Formatted amount: {balance_normalized:.6f} {token_symbol}")
                        
                        # Add to result
                        if token_type == "usdc":
                            network_balances[token_symbol] = {
                                "amount": str(balance),
                                "decimals": decimals,
                                "value": {
                                    "USDC": {
                                        "amount": str(balance),
                                        "decimals": decimals,
                                        "conversion_details": {
                                            "source": "Direct",
                                            "price_impact": "0.0000%",
                                            "rate": "1.000000",
                                            "fee_percentage": "0.0000%",
                                            "fallback": False,
                                            "note": "Direct 1:1 conversion"
                                        }
                                    }
                                }
                            }
                            print("✓ Direct 1:1 conversion with USDC")
                            usdc_value = balance_normalized
                        else:
                            usdc_amount, conversion = self._get_usdc_value(network, token_symbol, str(balance))
                            usdc_normalized = Decimal(usdc_amount) / Decimal(10**6)
                            
                            network_balances[token_symbol] = {
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
                            print(f"✓ Converted to USDC: {usdc_normalized:.6f} USDC")
                            print(f"  Rate: {conversion['rate']} USDC/{token_symbol}")
                            print(f"  Source: {conversion['source']}")
                            if conversion['note']:
                                print(f"  Note: {conversion['note']}")
                            
                            usdc_value = usdc_normalized
                        
                        # Update total
                        total_usdc_value += usdc_value
                
                print(f"\nNetwork {network} processing complete")
                # Only add network to result if it has balances
                if network_has_balance:
                    result[network] = network_balances
            
            # Update global USDC totals
            result["usdc_totals"]["total"]["wei"] = int(total_usdc_value * Decimal(10**6))
            result["usdc_totals"]["total"]["formatted"] = f"{total_usdc_value:.6f}"
            
            # Trier les tokens par valeur USDC décroissante pour chaque réseau
            for network in self.get_supported_networks():
                if network in result:
                    # Convertir le dictionnaire en liste de tuples (token, data)
                    tokens = list(result[network].items())
                    
                    # Trier par valeur USDC (en wei)
                    sorted_tokens = sorted(
                        tokens,
                        key=lambda x: int(x[1].get('value', {}).get('USDC', {}).get('amount', '0')),
                        reverse=True
                    )
                    
                    # Recréer le dictionnaire trié
                    result[network] = dict(sorted_tokens)
            
            print("\n" + "="*80)
            print(f"TOTAL SPOT VALUE: {total_usdc_value:.6f} USDC")
            print("="*80)
            
        except Exception as e:
            print(f"\n✗ Error getting spot token balances: {str(e)}")
        
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
    balances = manager.get_balances(test_address)
    
    print("\nSpot balances:")
    print(json.dumps(balances, indent=2))

if __name__ == "__main__":
    main() 