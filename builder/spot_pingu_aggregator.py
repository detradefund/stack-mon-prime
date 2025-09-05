import sys
from pathlib import Path
from typing import Dict, Any
import json
from decimal import Decimal
from web3 import Web3
from datetime import datetime, timezone
import time
import os

# Add parent directory and project root to PYTHONPATH
root_path = str(Path(__file__).parent.parent)
sys.path.append(root_path)
sys.path.append(str(Path(__file__).parent.parent))

from spot.balance_manager import SpotBalanceManager
from pingu.balance_manager import build_pingu_document

class SpotPinguAggregator:
    """
    Aggregator that combines balances from Spot and Pingu protocols.
    """
    
    def __init__(self):
        self.spot_manager = SpotBalanceManager()
        
    def get_all_balances(self, address: str) -> Dict[str, Any]:
        """
        Fetches and combines balances from Spot and Pingu protocols
        """
        # Get UTC timestamp before any on-chain requests
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        
        print("\n" + "="*80)
        print("FETCHING SPOT & PINGU BALANCES")
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
            print("  - Querying native MON balance")
            print("  - Querying balanceOf(address) for each token")
            print("  - Converting all tokens to MON and USDC using Crystal Price Indexer")
            
            spot_balances = self.spot_manager.get_balances(checksum_address)
            if spot_balances:
                result["spot"] = spot_balances
                print("✓ Spot positions fetched successfully")
        except Exception as e:
            print(f"✗ Error fetching Spot positions: {str(e)}")
            # Initialize empty spot structure
            result["spot"] = {}
        
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
                if "monad-testnet" in pingu_balances["protocols"]["pingu"]:
                    pingu_data = pingu_balances["protocols"]["pingu"]["monad-testnet"]
                    print(f"\nPingu positions on monad-testnet:")
                    
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
            if "monad-testnet" in protocol_data:
                pingu_data = protocol_data["monad-testnet"]
                if "totals" in pingu_data:
                    # Convert MON to readable format
                    mon_amount = Decimal(pingu_data["totals"]["mon"]) / Decimal(10**18)
                    key = f"{protocol_name}.monad-testnet.pool"
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
                    if "value" in token_data and "WETH" in token_data["value"]:
                        amount = Decimal(token_data["value"]["WETH"]["amount"]) / Decimal(10**18)
                        network_total += amount
            
            if network_total > 0:
                spot_totals[f"spot.{network}"] = f"{network_total:.6f}"
        
        # Add spot totals to positions
        positions.update(spot_totals)

    # Sort positions by value in descending order
    sorted_positions = dict(sorted(
        positions.items(),
        key=lambda x: Decimal(x[1]),
        reverse=True
    ))
    
    # Calculate total value from positions
    total_value = sum(Decimal(value) for value in sorted_positions.values())
    
    return {
        "nav": {
            "total_assets": f"{total_value:.6f}",
            "price_per_share": f"{total_value:.6f}",
            "total_supply": "1.000000",
            "total_assets_wei": str(int(total_value * Decimal(10**18)))
        },
        "positions": sorted_positions
    }

def main():
    """
    Main function to aggregate Spot and Pingu balance data.
    Uses command line argument if provided, otherwise uses default address.
    """
    # Default address from .env
    DEFAULT_ADDRESS = os.getenv('PRODUCTION_ADDRESS', '0x2EAc9dF8299e544b9d374Db06ad57AD96C7527c0')
    
    # Get address from command line argument if provided
    address = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ADDRESS
    
    if not Web3.is_address(address):
        print(f"Error: Invalid address format: {address}")
        return None
        
    # Create aggregator and get balances
    aggregator = SpotPinguAggregator()
    
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






