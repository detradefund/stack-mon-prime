import sys
from pathlib import Path
from typing import Dict, Any
import json
from decimal import Decimal
from web3 import Web3
from datetime import datetime, timezone
import time
import os
from dotenv import load_dotenv

# Add parent directory and project root to PYTHONPATH
root_path = str(Path(__file__).parent.parent)
sys.path.append(root_path)
sys.path.append(str(Path(__file__).parent.parent))

from spot.balance_manager import SpotBalanceManager
from pingu.balance_manager import build_pingu_document
from shares.supply_reader import SupplyReader

class BalanceAggregator:
    """
    Master aggregator that combines balances from Pingu and Spot protocols.
    Currently supports:
    - Pingu (Monad Testnet)
    - Spot (Monad Testnet)
    """
    
    def __init__(self):
        self.spot_manager = SpotBalanceManager()
        
    def get_all_balances(self, address: str) -> Dict[str, Any]:
        """
        Fetches and combines balances from Pingu and Spot protocols
        """
        # Get UTC timestamp before any on-chain requests
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        
        print("\n" + "="*80)
        print("FETCHING PROTOCOL BALANCES")
        print("="*80)
        
        # Convert address to checksum format
        checksum_address = Web3.to_checksum_address(address)
        
        # Initialize result structure
        result = {
            "protocols": {},
            "spot": {}
        }
        
        # Get spot balances
        try:
            print("\n" + "="*80)
            print("SPOT BALANCE MANAGER")
            print("="*80 + "\n")
            print("Processing method:")
            print("  - Querying native MON balance (excluded from totals - gas reserve)")
            print("  - Querying balanceOf(address) for each token")
            print("  - Converting all tokens to MON and USDC using Crystal Price Indexer")
            
            spot_balances = self.spot_manager.get_balances(checksum_address)
            if spot_balances:
                result["spot"] = spot_balances
                print("✓ Spot positions fetched successfully")
                
                # Add detailed logging for Spot
                for network, network_data in spot_balances.items():
                    if network == "totals":
                        continue
                    print(f"\nSpot positions on {network}:")
                    for token_symbol, token_data in network_data.items():
                        if token_symbol == "totals":
                            continue
                        print(f"\n{token_symbol}:")
                        print(f"  Amount: {token_data['formatted']}")
                        
                        if "value_mon" in token_data:
                            print(f"  Value in MON: {token_data['value_mon']}")
                        if "value_usdc" in token_data:
                            print(f"  Value in USDC: {token_data['value_usdc']}")
                        if "conversion_details" in token_data:
                            details = token_data["conversion_details"]
                            print(f"  Conversion source: {details['source']}")
                            print(f"  Note: {details['note']}")
                    
                    # Print network totals
                    if "totals" in network_data:
                        totals = network_data["totals"]
                        print(f"\nNetwork totals:")
                        print(f"  Total MON: {totals['formatted_mon']}")
                        print(f"  Total USDC: {totals['formatted_usdc']}")
                        if "note" in totals:
                            print(f"  Note: {totals['note']}")
                
                # Print overall totals
                if "totals" in spot_balances:
                    totals = spot_balances["totals"]
                    print(f"\nOverall totals:")
                    print(f"  Total MON: {totals['formatted_mon']}")
                    print(f"  Total USDC: {totals['formatted_usdc']}")
                    if "note" in totals:
                        print(f"  Note: {totals['note']}")
        except Exception as e:
            print(f"✗ Error fetching Spot positions: {str(e)}")
            # Initialize empty spot structure
            result["spot"] = {
                "monad-testnet": {
                    "MON": {
                        "amount": "0",
                        "decimals": 18,
                        "formatted": "0.000000",
                        "value_mon": "0",
                        "value_usdc": "0",
                        "conversion_details": {
                            "source": "Error",
                            "note": "Error fetching balances"
                        }
                    },
                    "totals": {
                        "mon": "0",
                        "usdc": "0",
                        "formatted_mon": "0.000000",
                        "formatted_usdc": "0.000000",
                        "note": "Error fetching balances"
                    }
                },
                "totals": {
                    "mon": "0",
                    "usdc": "0",
                    "formatted_mon": "0.000000",
                    "formatted_usdc": "0.000000",
                    "note": "Error fetching balances"
                }
            }
        
        # Get Pingu balances
        try:
            print("\n" + "="*80)
            print("PINGU BALANCE MANAGER")
            print("="*80 + "\n")
            print("Processing method:")
            print("  - Building Pingu document with manual balance input")
            print("  - Converting MON to WMON and USDC using Crystal Price Indexer")
            
            pingu_balances = build_pingu_document()
            if pingu_balances and pingu_balances.get("protocols", {}).get("pingu"):
                result["protocols"]["pingu"] = pingu_balances["protocols"]["pingu"]
                print("✓ Pingu positions fetched successfully")
                
                # Add detailed logging for Pingu
                pingu_data = pingu_balances["protocols"]["pingu"]
                print(f"\nPingu positions:")
                
                for token_symbol, token_data in pingu_data.items():
                    if token_symbol == "totals":
                        continue
                    print(f"\n{token_symbol}:")
                    print(f"  Amount: {Decimal(token_data['amount']) / Decimal(10**token_data['decimals']):.6f}")
                    
                    if "value" in token_data:
                        if "WMON" in token_data["value"]:
                            wmon_amount = Decimal(token_data["value"]["WMON"]["amount"]) / Decimal(10**18)
                            print(f"  Value in WMON: {wmon_amount:.6f}")
                            print(f"  Conversion rate: {token_data['value']['WMON']['conversion_details']['rate']}")
                            print(f"  Source: {token_data['value']['WMON']['conversion_details']['source']}")
                        
                        if "USDC" in token_data["value"]:
                            usdc_amount = Decimal(token_data["value"]["USDC"]["amount"]) / Decimal(10**6)
                            print(f"  Value in USDC: {usdc_amount:.2f}")
                            print(f"  Conversion rate: {token_data['value']['USDC']['conversion_details']['rate']}")
                            print(f"  Source: {token_data['value']['USDC']['conversion_details']['source']}")
                
                # Print totals
                if "totals" in pingu_data:
                    totals = pingu_data["totals"]
                    print(f"\nTotals:")
                    print(f"  Total MON: {Decimal(totals['mon']) / Decimal(10**18):.6f}")
                    print(f"  Total USDC: {Decimal(totals['usdc']) / Decimal(10**6):.2f}")
            else:
                print("✓ No Pingu positions found")
        except Exception as e:
            print(f"✗ Error fetching Pingu positions: {str(e)}")
        
        return result

def build_overview(all_balances: Dict[str, Any], address: str) -> Dict[str, Any]:
    """Build overview section with positions"""
    
    # Initialize positions dictionary
    positions = {}
    
    # Process each protocol's positions
    for protocol_name, protocol_data in all_balances["protocols"].items():
        if protocol_name == "pingu":
            # Handle Pingu data structure
            if "totals" in protocol_data:
                # Convert MON to WETH for consistency with other protocols
                mon_amount = Decimal(protocol_data["totals"]["mon"]) / Decimal(10**18)
                # For now, we'll use MON as the base unit since it's the native token
                key = f"{protocol_name}.pool"
                value = f"{mon_amount:.6f}"
                positions[key] = value

    # Process spot positions
    if "spot" in all_balances:
        # Initialize spot totals by network
        spot_totals = {}
        
        for network, network_data in all_balances["spot"].items():
            if network == "totals":
                continue
                
            network_total = Decimal('0')
            for token_name, token_data in network_data.items():
                if token_name != "totals" and isinstance(token_data, dict):
                    if "value_mon" in token_data:
                        amount = Decimal(token_data["value_mon"])
                        network_total += amount
            
            if network_total > 0:
                spot_totals[f"spot.{network}"] = f"{network_total:.6f}"
        
        # Add spot totals to positions
        positions.update(spot_totals)

    # Calculate total assets from protocol totals (Pingu + Spot)
    total_value = Decimal('0')
    
    # Add Pingu total
    if "pingu" in all_balances["protocols"]:
        pingu_data = all_balances["protocols"]["pingu"]
        if "totals" in pingu_data:
            pingu_mon = Decimal(pingu_data["totals"]["mon"]) / Decimal(10**18)
            total_value += pingu_mon
    
    # Add Spot total
    if "spot" in all_balances and "totals" in all_balances["spot"]:
        spot_mon = Decimal(all_balances["spot"]["totals"]["mon"])
        total_value += spot_mon

    # Sort positions by value in descending order
    sorted_positions = dict(sorted(
        positions.items(),
        key=lambda x: Decimal(x[1]),
        reverse=True
    ))
    
    # Get total supply from SupplyReader (with fallback)
    try:
        supply_reader = SupplyReader(address=address)
        total_supply = supply_reader.format_total_supply()
        total_supply_decimal = Decimal(total_supply)
    except Exception as e:
        print(f"Warning: Could not fetch total supply: {str(e)}")
        print("Using default total supply of 1000000.000000000000000000")
        total_supply = "1000000.000000000000000000"
        total_supply_decimal = Decimal(total_supply)
    
    # Calculate share price
    share_price = total_value / total_supply_decimal if total_supply_decimal != 0 else Decimal('0')
    
    return {
        "nav": {
            "total_assets": f"{total_value:.6f}",
            "price_per_share": f"{share_price:.6f}",
            "total_supply": total_supply,
            "total_assets_wei": str(int(total_value * Decimal(10**18)))
        },
        "positions": sorted_positions
    }

def main():
    """
    Main function to aggregate all balance data.
    Uses command line argument if provided, otherwise uses default address.
    """
    # Load environment variables
    load_dotenv()
    # Default address from environment
    DEFAULT_ADDRESS = os.getenv('PRODUCTION_ADDRESS')
    if not DEFAULT_ADDRESS:
        print("Error: Missing PRODUCTION_ADDRESS in environment")
        return None
    
    # Get address from command line argument if provided
    address = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ADDRESS
    
    if not Web3.is_address(address):
        print(f"Error: Invalid address format: {address}")
        return None
        
    # Create aggregator and get balances
    aggregator = BalanceAggregator()
    
    # Add retry logic for RPC calls
    max_retries = 3
    retry_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            all_balances = aggregator.get_all_balances(address)
            break
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Attempt {attempt + 1} failed: {str(e)}")
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print(f"All {max_retries} attempts failed")
                raise
    
    # Build the final result with overview, protocols and spot sections
    overview = build_overview(all_balances, address)
    
    # Format created_at to match timestamp format
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    
    final_result = {
        **overview,  # Add overview at the top
        "protocols": all_balances["protocols"],
        "spot": all_balances["spot"],
        "address": address,
        "created_at": created_at
    }
    
    # Display final result
    print("\n" + "="*80)
    print("FINAL AGGREGATED RESULT")
    print("="*80 + "\n")
    print(json.dumps(final_result, indent=2))
    
    return final_result

if __name__ == "__main__":
    main()
