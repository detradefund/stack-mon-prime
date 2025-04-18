import sys
from pathlib import Path
from typing import Dict, Any
import json
from decimal import Decimal
from web3 import Web3
from datetime import datetime, timezone

# Add parent directory to PYTHONPATH
root_path = str(Path(__file__).parent.parent)
sys.path.append(root_path)

from pendle.balance_manager import PendleBalanceManager, format_position_data as format_pendle_data
from convex.balance_manager import ConvexBalanceManager
from sky.balance_manager import BalanceManager as SkyBalanceManager
from tokemak.balance_manager import BalanceManager as TokemakBalanceManager, format_tokemak_data
from spot.balance_manager import SpotBalanceManager
from dtusdc.supply_reader import SupplyReader

class BalanceAggregator:
    """
    Master aggregator that combines balances from multiple protocols.
    Currently supports:
    - Pendle (Ethereum + Base)
    - Convex (Ethereum)
    - Sky Protocol (Ethereum + Base)
    - Tokemak (Ethereum)
    """
    
    def __init__(self):
        self.pendle_manager = PendleBalanceManager()
        self.convex_manager = ConvexBalanceManager()
        self.sky_manager = SkyBalanceManager()
        self.tokemak_manager = TokemakBalanceManager()
        self.spot_manager = SpotBalanceManager()
        
    def get_all_balances(self, address: str) -> Dict[str, Any]:
        """
        Fetches and combines balances from all supported protocols
        
        Args:
            address: Ethereum address to check
            
        Returns:
            Combined balance data from all protocols with USDC valuations
        """
        # Get UTC timestamp before any on-chain requests
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        
        print("\n" + "="*80)
        print("FETCHING PROTOCOL BALANCES")
        print("="*80)
        
        # Convert address to checksum format
        checksum_address = Web3.to_checksum_address(address)
        
        result = {}
        total_usdc = 0
        
        # Get Pendle balances
        try:
            pendle_balances = self.pendle_manager.get_balances(checksum_address)
            if pendle_balances:
                formatted_pendle = format_pendle_data(pendle_balances)
                result.update(formatted_pendle)
                total_usdc += int(formatted_pendle["pendle"]["usdc_totals"]["total"]["wei"])
                print("✓ Pendle positions fetched successfully")
        except Exception as e:
            print(f"✗ Error fetching Pendle positions: {str(e)}")
        
        # Get Convex balances
        try:
            convex_balances = self.convex_manager.get_balances(checksum_address)
            if convex_balances:
                result.update(convex_balances)
                if "convex" in convex_balances:
                    for chain_data in convex_balances["convex"].values():
                        for pool_data in chain_data.values():
                            if "usdc_totals" in pool_data:
                                total_usdc += int(pool_data["usdc_totals"]["total"]["wei"])
                print("✓ Convex positions fetched successfully")
        except Exception as e:
            print(f"✗ Error fetching Convex positions: {str(e)}")

        # Get Sky Protocol balances
        try:
            sky_balances = self.sky_manager.get_balances(checksum_address)
            if sky_balances and "sky" in sky_balances:
                result.update(sky_balances)
                if "usdc_totals" in sky_balances["sky"]:
                    total_usdc += int(sky_balances["sky"]["usdc_totals"]["total"]["wei"])
                print("✓ Sky Protocol positions fetched successfully")
        except Exception as e:
            print(f"✗ Error fetching Sky Protocol positions: {str(e)}")

        # Get Tokemak balances
        try:
            tokemak_balances = self.tokemak_manager.get_balances(checksum_address)
            if tokemak_balances:
                formatted_tokemak = format_tokemak_data(tokemak_balances)
                result.update(formatted_tokemak)
                if "tokemak" in formatted_tokemak:
                    chain_data = formatted_tokemak["tokemak"]["ethereum"]
                    if "usdc_totals" in chain_data:
                        total_usdc += int(chain_data["usdc_totals"]["total"]["wei"])
                print("✓ Tokemak positions fetched successfully")
        except Exception as e:
            print(f"✗ Error fetching Tokemak positions: {str(e)}")

        # Get spot balances
        try:
            spot_balances = self.spot_manager.get_balances(checksum_address)
            if spot_balances:
                print("✓ Spot positions fetched successfully")
        except Exception as e:
            print(f"✗ Error fetching Spot positions: {str(e)}")
            spot_balances = {}

        # Add global USDC total across PROTOCOLS ONLY (not including spot)
        result["usdc_totals"] = {
            "total": {
                "wei": total_usdc,
                "formatted": f"{total_usdc/1e6:.2f}"
            }
        }
        
        # Create a sorted list of protocols based on their USDC totals
        protocol_totals = []
        
        # Add Sky if exists
        if "sky" in result and "usdc_totals" in result["sky"]:
            protocol_totals.append(
                ("sky", int(result["sky"]["usdc_totals"]["total"]["wei"]))
            )
        
        # Add Pendle if exists
        if "pendle" in result and "usdc_totals" in result["pendle"]:
            protocol_totals.append(
                ("pendle", int(result["pendle"]["usdc_totals"]["total"]["wei"]))
            )
        
        # Add Tokemak if exists
        if ("tokemak" in result and 
            "ethereum" in result["tokemak"] and 
            "usdc_totals" in result["tokemak"]["ethereum"]):
            protocol_totals.append(
                ("tokemak", int(result["tokemak"]["ethereum"]["usdc_totals"]["total"]["wei"]))
            )
        
        # Add Convex if exists
        if "convex" in result:
            convex_total = sum(
                int(pool_data["usdc_totals"]["total"]["wei"])
                for chain_data in result["convex"].values()
                for pool_data in chain_data.values()
                if isinstance(pool_data, dict) and "usdc_totals" in pool_data
            )
            protocol_totals.append(("convex", convex_total))
        
        # Sort protocols by USDC value in descending order
        protocol_totals.sort(key=lambda x: x[1], reverse=True)
        
        # Create new ordered dictionary with sorted protocols
        ordered_balances = {
            protocol: result[protocol]
            for protocol, _ in protocol_totals
            if protocol in result  # Additional safety check
        }
        
        # Add the global USDC totals at the end
        ordered_balances["usdc_totals"] = result["usdc_totals"]
        
        # Create the final result with both protocols and spot balances
        final_result = {
            "timestamp": timestamp,
            "protocols": ordered_balances,
            "spot": spot_balances
        }
        
        return final_result

def build_overview(all_balances: Dict[str, Any]) -> Dict[str, Any]:
    """Build overview section with summary and positions"""
    
    # Calculate summary values
    protocols_value = Decimal(all_balances["protocols"]["usdc_totals"]["total"]["formatted"])
    spot_value = Decimal(all_balances["spot"]["usdc_totals"]["total"]["formatted"])
    total_value = protocols_value + spot_value
    
    # Get total supply from SupplyReader
    supply_reader = SupplyReader()
    total_supply = supply_reader.format_total_supply()
    
    # Calculate share price (total value / total supply)
    total_supply_decimal = Decimal(total_supply)
    share_price = total_value / total_supply_decimal if total_supply_decimal != 0 else Decimal('0')
    
    # Initialize positions dictionary
    positions = {}
    
    # Get Sky Protocol positions
    if "sky" in all_balances["protocols"]:
        for network, network_data in all_balances["protocols"]["sky"].items():
            if isinstance(network_data, dict) and "sUSDS" in network_data:
                key = f"sky.{network}.sUSDS"
                value = network_data["sUSDS"]["value"]["USDC"]["amount"]
                positions[key] = str(Decimal(value) / Decimal(1e6))
    
    # Get Pendle positions
    if "pendle" in all_balances["protocols"]:
        for network, network_data in all_balances["protocols"]["pendle"].items():
            if isinstance(network_data, dict):
                for token, token_data in network_data.items():
                    if isinstance(token_data, dict) and "value" in token_data:
                        key = f"pendle.{network}.{token}"
                        value = token_data["value"]["USDC"]["amount"]
                        positions[key] = str(Decimal(value) / Decimal(1e6))
    
    # Get Convex positions
    if "convex" in all_balances["protocols"]:
        for network, network_data in all_balances["protocols"]["convex"].items():
            for pool_name, pool_data in network_data.items():
                if isinstance(pool_data, dict) and "usdc_totals" in pool_data:
                    key = f"convex.{network}.{pool_name}"
                    value = pool_data["usdc_totals"]["total"]["wei"]
                    positions[key] = str(Decimal(value) / Decimal(1e6))
    
    # Sort positions by value in descending order
    sorted_positions = dict(sorted(
        positions.items(),
        key=lambda x: Decimal(x[1]),
        reverse=True
    ))
    
    return {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "nav": {
            "usdc": str(total_value),
            "share_price": str(share_price),
            "total_supply": total_supply
        },
        "overview": {
            "summary": {
                "total_value_usdc": str(total_value),
                "protocols_value_usdc": str(protocols_value),
                "spot_value_usdc": str(spot_value)
            },
            "positions": sorted_positions
        }
    }

def main():
    """
    CLI utility for testing balance aggregation.
    Accepts address as argument or uses DEFAULT_USER_ADDRESS from environment.
    """
    from dotenv import load_dotenv
    import os
    
    # Load environment variables
    load_dotenv()
    
    # Get test address
    test_address = sys.argv[1] if len(sys.argv) > 1 else os.getenv('DEFAULT_USER_ADDRESS')
    
    if not test_address:
        print("Error: No address provided and DEFAULT_USER_ADDRESS not found in .env")
        sys.exit(1)
    
    # Create aggregator and get balances
    aggregator = BalanceAggregator()
    all_balances = aggregator.get_all_balances(test_address)
    
    # Create a sorted list of protocols based on their USDC totals
    protocol_totals = []
    
    # Add protocols only if they exist
    if "sky" in all_balances["protocols"]:
        protocol_totals.append(
            ("sky", int(all_balances["protocols"]["sky"]["usdc_totals"]["total"]["wei"]))
        )
    
    if "pendle" in all_balances["protocols"]:
        protocol_totals.append(
            ("pendle", int(all_balances["protocols"]["pendle"]["usdc_totals"]["total"]["wei"]))
        )
    
    if ("tokemak" in all_balances["protocols"] and 
        "ethereum" in all_balances["protocols"]["tokemak"] and 
        "usdc_totals" in all_balances["protocols"]["tokemak"]["ethereum"]):
        protocol_totals.append(
            ("tokemak", int(all_balances["protocols"]["tokemak"]["ethereum"]["usdc_totals"]["total"]["wei"]))
        )
    
    if "convex" in all_balances["protocols"]:
        convex_total = sum(int(pool_data["usdc_totals"]["total"]["wei"]) 
                          for chain_data in all_balances["protocols"]["convex"].values() 
                          for pool_data in chain_data.values() 
                          if isinstance(pool_data, dict) and "usdc_totals" in pool_data)
        protocol_totals.append(("convex", convex_total))
    
    # Sort protocols by USDC value in descending order
    protocol_totals.sort(key=lambda x: x[1], reverse=True)
    
    # Create new ordered dictionary with sorted protocols
    ordered_balances = {
        protocol: all_balances["protocols"][protocol]
        for protocol, _ in protocol_totals
    }
    
    # Add the global USDC totals at the end
    ordered_balances["usdc_totals"] = all_balances["protocols"]["usdc_totals"]
    
    # Build the final result with overview, protocols and spot sections
    overview = build_overview(all_balances)
    final_result = {
        **overview,  # Add overview at the top
        "protocols": ordered_balances,
        "spot": all_balances["spot"]
    }
    
    # Display final result
    print("\n" + "="*80)
    print("FINAL AGGREGATED RESULT")
    print("="*80 + "\n")
    print(json.dumps(final_result, indent=2))
    
    return final_result

if __name__ == "__main__":
    results = main()
