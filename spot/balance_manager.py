from web3 import Web3
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from decimal import Decimal
import time
import os
from dotenv import load_dotenv

# Add parent directory to PYTHONPATH
root_path = str(Path(__file__).parent.parent)
sys.path.append(root_path)

from config.networks import NETWORK_TOKENS, RPC_URLS
from utils.retry import Web3Retry
from crystal.price_indexer import CrystalPriceIndexer

# Load environment variables
load_dotenv()
# Production address from environment
PRODUCTION_ADDRESS = os.getenv('PRODUCTION_ADDRESS')

class SpotBalanceManager:
    """Unified Spot Balance Manager - Handles raw balances and price conversions"""
    
    def __init__(self, enable_prices: bool = True, verbose: bool = False):
        """
        Initialize the balance manager
        
        Args:
            enable_prices: Whether to enable price conversions using Crystal Price Indexer
            verbose: Whether to enable verbose output
        """
        self.enable_prices = enable_prices
        self.verbose = verbose
        
        # Initialize Web3 connections for each network
        self.connections = {
            "monad-testnet": Web3(Web3.HTTPProvider(RPC_URLS['monad-testnet']))
        }
        
        # Initialize contracts for each network
        self.contracts = self._init_contracts()
        
        # Initialize Crystal Price Indexer if prices are enabled
        self.price_indexer = None
        if self.enable_prices:
            try:
                self.price_indexer = CrystalPriceIndexer("monad-testnet")
                if self.verbose:
                    print(f"Crystal Price Indexer initialized - {len(self.price_indexer.crystal_pools)} pools")
            except Exception as e:
                print(f"Warning: Could not initialize Crystal Price Indexer: {str(e)}")
                self.enable_prices = False

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
            # Get all tokens for the network
            for symbol, token_data in NETWORK_TOKENS[network].items():
                # Skip yield-bearing tokens
                if token_data.get("type") == "yield-bearing":
                    continue
                    
                if symbol not in contracts:
                    contracts[symbol] = {}
                
                contracts[symbol][network] = w3.eth.contract(
                    address=Web3.to_checksum_address(token_data["address"]),
                    abi=abi
                )
                
        return contracts

    def convert_token_to_mon_and_usdc(self, amount: Decimal, token_symbol: str) -> tuple[Decimal, Decimal, Dict[str, Any]]:
        """
        Convert token amount to MON and USDC using Crystal Price Indexer
        Returns (mon_amount, usdc_amount, conversion_details)
        """
        if not self.enable_prices or not self.price_indexer:
            return Decimal("0"), Decimal("0"), {
                "source": "Disabled",
                "mon_price": "0",
                "usdc_price": "0",
                "conversion_type": "disabled",
                "route_mon": "Prices disabled",
                "route_usdc": "Prices disabled",
                "note": "Price conversions are disabled"
            }
        
        try:
            if token_symbol == "MON":
                # MON is already in MON, convert to USDC
                mon_usdc_price = self.price_indexer.get_mon_usdc_price()
                if mon_usdc_price and mon_usdc_price > 0:
                    usdc_amount = amount * mon_usdc_price
                else:
                    usdc_amount = Decimal("0")
                
                return amount, usdc_amount, {
                    "source": "Direct",
                    "mon_price": "1.000000",
                    "usdc_price": str(usdc_amount / amount) if amount > 0 else "0",
                    "conversion_type": "direct",
                    "route_mon": "MON -> MON (direct)",
                    "route_usdc": "MON -> USDC (1 step)",
                    "note": "Direct 1:1 conversion (MON)"
                }
            
            if token_symbol == "WMON":
                # WMON is equivalent to MON (1:1), convert to USDC
                mon_usdc_price = self.price_indexer.get_mon_usdc_price()
                if mon_usdc_price and mon_usdc_price > 0:
                    usdc_amount = amount * mon_usdc_price
                else:
                    usdc_amount = Decimal("0")
                
                return amount, usdc_amount, {
                    "source": "Direct",
                    "mon_price": "1.000000",
                    "usdc_price": str(usdc_amount / amount) if amount > 0 else "0",
                    "conversion_type": "direct",
                    "route_mon": "WMON -> MON (1:1) -> MON (direct)",
                    "route_usdc": "WMON -> MON (1:1) -> USDC (1 step)",
                    "note": "WMON treated as MON equivalent (1:1 conversion)"
                }
            
            # Use Crystal Price Indexer to get conversion rates
            if token_symbol == "WMON":
                # WMON to MON conversion (1:1)
                mon_amount = amount
                # WMON to USDC conversion via MON
                mon_usdc_price = self.price_indexer.get_mon_usdc_price()
                if mon_usdc_price and mon_usdc_price > 0:
                    usdc_amount = amount * mon_usdc_price
                else:
                    usdc_amount = Decimal("0")
            elif token_symbol == "USDC":
                # USDC to MON conversion
                mon_usdc_price = self.price_indexer.get_mon_usdc_price()
                if mon_usdc_price and mon_usdc_price > 0:
                    mon_amount = amount / mon_usdc_price
                else:
                    mon_amount = Decimal("0")
                # USDC to USDC is direct
                usdc_amount = amount
            else:
                # Other tokens - try to get price in MON
                token_price_in_mon = self.price_indexer.get_token_price_in_mon(token_symbol)
                if token_price_in_mon and token_price_in_mon > 0:
                    mon_amount = amount * token_price_in_mon
                    # Convert MON to USDC
                    mon_usdc_price = self.price_indexer.get_mon_usdc_price()
                    if mon_usdc_price and mon_usdc_price > 0:
                        usdc_amount = mon_amount * mon_usdc_price
                    else:
                        usdc_amount = Decimal("0")
                else:
                    mon_amount = Decimal("0")
                    usdc_amount = Decimal("0")
            
            if mon_amount is None:
                mon_amount = Decimal("0")
            if usdc_amount is None:
                usdc_amount = Decimal("0")
            
            # Calculate prices
            mon_price = mon_amount / amount if amount > 0 else Decimal("0")
            usdc_price = usdc_amount / amount if amount > 0 else Decimal("0")
            
            # Determine routes based on token type - always shortest route
            if token_symbol == "USDC":
                route_mon = f"{token_symbol} -> MON (1 step)"
                route_usdc = f"{token_symbol} -> USDC (direct)"
            elif token_symbol in ["PINGU", "aprMON", "sMON", "shMON"]:
                # For these tokens, check if direct USDC pool exists
                direct_usdc_pool = f"{token_symbol}/USDC"
                if direct_usdc_pool in self.price_indexer.crystal_pools:
                    route_mon = f"{token_symbol} -> MON (1 step)"
                    route_usdc = f"{token_symbol} -> USDC (1 step)"
                else:
                    route_mon = f"{token_symbol} -> MON (1 step)"
                    route_usdc = f"{token_symbol} -> MON -> USDC (2 steps)"
            else:
                route_mon = f"{token_symbol} -> MON (1 step)"
                route_usdc = f"{token_symbol} -> USDC (1 step)"
            
            return mon_amount, usdc_amount, {
                "source": "Crystal",
                "mon_price": str(mon_price),
                "usdc_price": str(usdc_price),
                "conversion_type": "crystal_swap",
                "route_mon": route_mon,
                "route_usdc": route_usdc,
                "note": f"Converted via Crystal Price Indexer"
            }
            
        except Exception as e:
            return Decimal("0"), Decimal("0"), {
                "source": "Error",
                "mon_price": "0",
                "usdc_price": "0",
                "conversion_type": "error",
                "route_mon": "Error",
                "route_usdc": "Error",
                "note": f"Technical error: {str(e)[:200]}"
            }

    def get_balances(self, address: str) -> Dict[str, Any]:
        """
        Get all token balances for an address with optional price conversions.
        """
        if self.enable_prices:
            print("\nProcessing method:")
            print("  - Querying native MON balance (excluded from totals - gas reserve)")
            print("  - Querying balanceOf(address) for each token")
            print("  - Converting all tokens to MON and USDC using Crystal Price Indexer")
        else:
            print("\nProcessing method:")
            print("  - Querying native MON balance (excluded from totals - gas reserve)")
            print("  - Querying balanceOf(address) for each token")
            print("  - Returning raw balances (no conversions)")
        
        checksum_address = Web3.to_checksum_address(address)
        result = {}
        total_mon = Decimal("0")
        total_usdc = Decimal("0")
        
        try:
            # Process each network
            for network in self.get_supported_networks():
                print(f"\nProcessing network: {network}")
                network_total_mon = Decimal("0")
                network_total_usdc = Decimal("0")
                
                # Initialize network structure
                network_result = {}
                
                try:
                    # Check native MON balance first
                    native_balance = self.connections[network].eth.get_balance(checksum_address)
                    
                    print(f"\nProcessing native MON:")
                    print(f"  Amount: {Decimal(native_balance) / Decimal(10**18):.6f} MON")
                    
                    if native_balance > 0:
                        # Native MON is already in MON terms
                        mon_amount = Decimal(native_balance) / Decimal(10**18)
                        
                        if self.enable_prices and self.price_indexer:
                            mon_usdc_price = self.price_indexer.get_mon_usdc_price()
                            if mon_usdc_price and mon_usdc_price > 0:
                                usdc_amount = mon_amount * mon_usdc_price
                            else:
                                usdc_amount = Decimal("0")
                            
                            # Note: Native MON excluded from totals (reserved for gas fees)
                            # network_total_mon += mon_amount
                            # network_total_usdc += usdc_amount
                            # total_mon += mon_amount
                            # total_usdc += usdc_amount
                            
                            print(f"  → Converted to: {mon_amount:.6f} MON / {usdc_amount:.2f} USDC (excluded from totals - gas reserve)")
                            
                            # Don't add native MON to network_result - completely excluded
                            # network_result["MON"] = { ... }
                        else:
                            # Raw balance only - don't add native MON to results
                            pass
                    else:
                        print("  → Balance is 0, skipping")
                except Exception as e:
                    print(f"Error checking native MON balance: {str(e)}")
                
                # Process each token type
                for token_type, network_contracts in self.contracts.items():
                    if network not in network_contracts:
                        continue
                        
                    contract = network_contracts[network]
                    balance = Web3Retry.call_contract_function(
                        contract.functions.balanceOf(checksum_address).call
                    )
                    
                    token_symbol = token_type
                    decimals = NETWORK_TOKENS[network][token_symbol]["decimals"]
                    balance_normalized = Decimal(balance) / Decimal(10**decimals)
                    
                    print(f"\nProcessing token: {token_symbol}")
                    print(f"  Amount: {balance_normalized:.6f} {token_symbol}")
                    
                    if balance > 0:
                        if self.enable_prices and self.price_indexer:
                            # Convert token to MON and USDC
                            mon_amount, usdc_amount, conversion_details = self.convert_token_to_mon_and_usdc(balance_normalized, token_symbol)
                            
                            network_total_mon += mon_amount
                            network_total_usdc += usdc_amount
                            total_mon += mon_amount
                            total_usdc += usdc_amount
                            
                            print(f"  → Converted to: {mon_amount:.6f} MON / {usdc_amount:.2f} USDC")
                            
                            # Add token data with conversions
                            network_result[token_symbol] = {
                                "amount": str(balance),
                                "decimals": decimals,
                                "formatted": f"{balance_normalized:.6f}",
                                "address": NETWORK_TOKENS[network][token_symbol]["address"],
                                "value_mon": str(mon_amount),
                                "value_usdc": str(usdc_amount),
                                "conversion_details": conversion_details
                            }
                        else:
                            # Raw balance only
                            network_result[token_symbol] = {
                                "amount": str(balance),
                                "decimals": decimals,
                                "formatted": f"{balance_normalized:.6f}",
                                "address": NETWORK_TOKENS[network][token_symbol]["address"]
                            }
                    else:
                        print("  → Balance is 0, skipping")
                
                # Add network totals only if there are balances
                if network_result:
                    if self.enable_prices and self.price_indexer:
                        network_result["totals"] = {
                            "mon": str(network_total_mon),
                            "usdc": str(network_total_usdc),
                            "formatted_mon": f"{network_total_mon:.6f}",
                            "formatted_usdc": f"{network_total_usdc:.6f}",
                            "note": "Native MON excluded (gas reserve)"
                        }
                    # Only add network to result if it has balances
                    result[network] = network_result
            
            # Add protocol total only if there are balances
            if total_mon > 0 and self.enable_prices and self.price_indexer:
                result["totals"] = {
                    "mon": str(total_mon),
                    "usdc": str(total_usdc),
                    "formatted_mon": f"{total_mon:.6f}",
                    "formatted_usdc": f"{total_usdc:.6f}",
                    "note": "Native MON excluded (gas reserve)"
                }

            if self.enable_prices and self.price_indexer:
                print(f"\n[Spot] Calculation complete - Total: {total_mon:.6f} MON / {total_usdc:.2f} USDC")
            else:
                print(f"\n[Spot] Balance fetch complete")
            return result
            
        except Exception as e:
            print(f"\nError processing spot balances: {str(e)}")
            return result

    def get_balances_simple(self, address: str) -> Dict[str, Any]:
        """
        Get raw balances only (without price conversions)
        """
        # Temporarily disable prices
        original_enable_prices = self.enable_prices
        self.enable_prices = False
        
        try:
            result = self.get_balances(address)
            return result
        finally:
            # Restore original setting
            self.enable_prices = original_enable_prices

    def format_balance(self, balance: int, decimals: int) -> str:
        """Format raw balance to human readable format"""
        return str(Decimal(balance) / Decimal(10**decimals))

    def get_supported_networks(self) -> list:
        """Get supported networks"""
        return list(self.connections.keys())
    
    def get_protocol_info(self) -> dict:
        """Get protocol information"""
        if self.enable_prices:
            return {
                "name": "Spot Tokens with MON Conversion",
                "description": "Token balances converted to MON using Crystal Price Indexer"
            }
        else:
            return {
                "name": "Spot Tokens (Simple)",
                "description": "Raw token balances without price conversions"
            }

def main():
    import json
    
    # Parse command line arguments
    enable_prices = True
    verbose = False
    
    # Check for flags
    if "--no-prices" in sys.argv:
        enable_prices = False
        sys.argv.remove("--no-prices")
    
    if "--verbose" in sys.argv:
        verbose = True
        sys.argv.remove("--verbose")
    
    # Use command line argument if provided, otherwise use production address
    test_address = sys.argv[1] if len(sys.argv) > 1 else PRODUCTION_ADDRESS
    
    print(f"=== Spot Balance Manager ===")
    print(f"Address: {test_address}")
    print(f"Price conversions: {'Enabled' if enable_prices else 'Disabled'}")
    print(f"Verbose: {'Yes' if verbose else 'No'}")
    
    manager = SpotBalanceManager(enable_prices=enable_prices, verbose=verbose)
    balances = manager.get_balances(test_address)
    
    print("\n" + "="*80)
    print("FINAL RESULT:")
    print("="*80 + "\n")
    print(json.dumps(balances, indent=2))

if __name__ == "__main__":
    main() 