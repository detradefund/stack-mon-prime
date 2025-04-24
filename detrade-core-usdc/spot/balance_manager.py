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
from cowswap.cow_client import get_quote

class SpotBalanceManager:
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
        contracts = {}
        
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
        
        # Initialize contracts for each network
        for network, w3 in self.connections.items():
            # Get all spot tokens (those without 'protocol' key)
            spot_tokens = {
                symbol: token_data  # Keep original case
                for symbol, token_data in NETWORK_TOKENS[network].items()
                if "protocol" not in token_data
            }
            
            # Initialize contract for each token
            for symbol, token_data in spot_tokens.items():
                if symbol not in contracts:
                    contracts[symbol] = {}
                
                contracts[symbol][network] = w3.eth.contract(
                    address=Web3.to_checksum_address(token_data["address"]),
                    abi=abi
                )
                
        return contracts

    def _get_usdc_value(self, network: str, token_symbol: str, amount: str) -> tuple[str, dict]:
        """
        Get USDC value for a given token amount using CoWSwap
        Returns (usdc_amount, conversion_details)
        """
        try:
            # Get token contract address and decimals
            token_address = NETWORK_TOKENS[network][token_symbol]["address"]
            token_decimals = NETWORK_TOKENS[network][token_symbol]["decimals"]

            # Get quote from CoW Protocol
            result = get_quote(
                network=network,
                sell_token=token_address,
                buy_token=NETWORK_TOKENS[network]["USDC"]["address"],
                amount=amount,
                token_decimals=token_decimals,
                token_symbol=token_symbol
            )

            if result["quote"]:
                return result["quote"]["quote"]["buyAmount"], result["conversion_details"]

            return "0", result["conversion_details"]

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
        print("\n" + "="*80)
        print("SPOT BALANCE MANAGER")
        print("="*80)
        
        print("\nProcessing method:")
        print("  - Querying balanceOf(address) for each token")
        print("  - Converting non-USDC tokens to USDC via CoWSwap")
        
        checksum_address = Web3.to_checksum_address(address)
        result = {
            "usdc_totals": {
                "total": {
                    "wei": 0,
                    "formatted": "0.000000"
                }
            }
        }
        total_usdc_wei = 0
        
        try:
            total_usdc_value = Decimal('0')
            
            # Process each network
            for network in self.get_supported_networks():
                print(f"\nProcessing network: {network}")
                network_has_balance = False
                network_balances = {}
                network_total = 0
                
                # Process each token type
                for token_type, network_contracts in self.contracts.items():
                    if network not in network_contracts:
                        continue
                        
                    contract = network_contracts[network]
                    balance = contract.functions.balanceOf(checksum_address).call()
                    
                    token_symbol = token_type
                    decimals = NETWORK_TOKENS[network][token_symbol]["decimals"]
                    balance_normalized = Decimal(balance) / Decimal(10**decimals)
                    
                    print(f"\nProcessing token: {token_symbol}")
                    print(f"  Amount: {balance_normalized:.6f} {token_symbol}")
                    
                    if balance > 0:
                        network_has_balance = True
                        usdc_amount, conversion_details = self._get_usdc_value(network, token_symbol, str(balance))
                        usdc_normalized = Decimal(usdc_amount) / Decimal(10**6)
                        network_total += int(usdc_amount)
                        
                        network_balances[token_symbol] = {
                            "amount": str(balance),
                            "decimals": decimals,
                            "value": {
                                "USDC": {
                                    "amount": usdc_amount,
                                    "decimals": 6,
                                    "conversion_details": conversion_details
                                }
                            }
                        }
                        
                        total_usdc_value += usdc_normalized
                    else:
                        print("  → Balance is 0, skipping conversion")
                
                print(f"\nNetwork {network} processing complete")
                # Only add network to result if it has balances
                if network_has_balance:
                    # Save current totals
                    current_totals = result["usdc_totals"]
                    
                    # Add network
                    result[network] = network_balances
                    result[network]["usdc_totals"] = {
                        "total": {
                            "wei": network_total,
                            "formatted": f"{network_total/1e6:.6f}"
                        }
                    }
                    
                    # Restore totals
                    result["usdc_totals"] = current_totals
            
            # Sort tokens by USDC value for each network
            for network in self.get_supported_networks():
                if network in result:
                    tokens = [(k, v) for k, v in result[network].items() if k != "usdc_totals"]
                    sorted_tokens = sorted(
                        tokens,
                        key=lambda x: int(x[1].get('value', {}).get('USDC', {}).get('amount', '0')),
                        reverse=True
                    )
                    result[network].update(dict(sorted_tokens))
            
            # Calculate global total at the end
            total_usdc_wei = sum(
                network_data["usdc_totals"]["total"]["wei"]
                for network_data in result.values()
                if isinstance(network_data, dict) and "usdc_totals" in network_data
                and network_data != result["usdc_totals"]  # Exclude global total
            )

            # Update global total
            result["usdc_totals"] = {
                "total": {
                    "wei": total_usdc_wei,
                    "formatted": f"{total_usdc_wei/1e6:.6f}"
                }
            }

            # Display summary
            print("\n[Spot] Calculation complete")
            
            # Display positions by network and token
            for network in result:
                if network != "usdc_totals":
                    for token_symbol, token_data in result[network].items():
                        if token_symbol != "usdc_totals":
                            amount = int(token_data["value"]["USDC"]["amount"])
                            if amount > 0:
                                print(f"spot.{network}.{token_symbol}: {amount/1e6:.6f} USDC")

            # Move usdc_totals to the end
            final_result = {}
            for network in result:
                if network != "usdc_totals":
                    final_result[network] = result[network]
            final_result["usdc_totals"] = result["usdc_totals"]

        except Exception as e:
            print(f"\n✗ Error getting spot token balances: {str(e)}")
            return {
                "usdc_totals": {
                    "total": {
                        "wei": 0,
                        "formatted": "0.000000"
                    }
                }
            }
        
        return final_result

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
                },
                "PENDLE": {  # Add PENDLE token
                    "ethereum": NETWORK_TOKENS["ethereum"]["PENDLE"]
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