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
from tokemak.balance_manager import BalanceManager as TokemakBalanceManager
from spot.balance_manager import SpotBalanceManager
from shares.supply_reader import SupplyReader
from equilibria.balance_manager import BalanceManager as EquilibriaBalanceManager

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
        self.equilibria_manager = EquilibriaBalanceManager()
        
    def get_all_balances(self, address: str) -> Dict[str, Any]:
        """
        Fetches and combines balances from all supported protocols
        """
        # Get UTC timestamp before any on-chain requests
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        
        print("\n" + "="*80)
        print("FETCHING PROTOCOL BALANCES")
        print("="*80)
        
        # Convert address to checksum format
        checksum_address = Web3.to_checksum_address(address)
        
        result = {}
        
        # Get pendle balances
        try:
            pendle_balances = self.pendle_manager.get_balances(checksum_address)
            if pendle_balances:
                result.update(pendle_balances)
                print("✓ Pendle positions fetched successfully")
        except Exception as e:
            print(f"✗ Error fetching Pendle positions: {str(e)}")
        
        # Get Convex balances
        try:
            convex_balances = self.convex_manager.get_balances(checksum_address)
            if convex_balances:
                result.update(convex_balances)
                print("✓ Convex positions fetched successfully")
        except Exception as e:
            print(f"✗ Error fetching Convex positions: {str(e)}")

        # Get Sky Protocol balances
        try:
            sky_balances = self.sky_manager.get_balances(checksum_address)
            if sky_balances and "sky" in sky_balances:
                result.update(sky_balances)
                print("✓ Sky Protocol positions fetched successfully")
        except Exception as e:
            print(f"✗ Error fetching Sky Protocol positions: {str(e)}")

        # Get Equilibria balances
        try:
            equilibria_balances = self.equilibria_manager.get_balances(checksum_address)
            if (equilibria_balances and 
                "equilibria" in equilibria_balances and 
                "ethereum" in equilibria_balances["equilibria"] and
                "GHO-USR" in equilibria_balances["equilibria"]["ethereum"] and
                int(equilibria_balances["equilibria"]["ethereum"]["GHO-USR"]["amount"]) > 0):
                
                result.update(equilibria_balances)
                print("✓ Equilibria positions fetched successfully")
        except Exception as e:
            print(f"✗ Error fetching Equilibria positions: {str(e)}")
        
        # Get Tokemak balances
        try:
            tokemak_balances = self.tokemak_manager.get_balances(checksum_address)
            if tokemak_balances:
                result.update(tokemak_balances)
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
            spot_balances = {
                "spot": {
                    "ethereum": {
                        "totals": {
                            "wei": 0,
                            "formatted": "0.000000"
                        }
                    },
                    "base": {
                        "totals": {
                            "wei": 0,
                            "formatted": "0.000000"
                        }
                    }
                }
            }

        # Create the final result with both protocols and spot balances
        final_result = {
            "timestamp": timestamp,
            "protocols": result,
            "spot": spot_balances
        }
        
        return final_result

def build_overview(all_balances: Dict[str, Any], address: str) -> Dict[str, Any]:
    """Build overview section with positions"""
    
    # Initialize positions dictionary
    positions = {}
    
    # Process each protocol's positions
    for protocol_name, protocol_data in all_balances["protocols"].items():
        # For protocols with direct totals (Sky, Pendle, Tokemak)
        if "totals" in protocol_data:
            for network, network_data in protocol_data.items():
                if network == "totals":
                    continue
                for token_name, token_data in network_data.items():
                    if token_name != "totals" and isinstance(token_data, dict):
                        if "totals" in token_data:
                            key = f"{protocol_name}.{network}.{token_name}"
                            value = f"{Decimal(token_data['totals']['formatted']):.6f}"
                            positions[key] = value
        
        # For protocols with pools (Convex, Equilibria)
        elif protocol_name in ["convex", "equilibria"]:
            for network, network_data in protocol_data.items():
                if network == "totals":
                    continue
                for pool_name, pool_data in network_data.items():
                    if pool_name != "totals" and isinstance(pool_data, dict):
                        if "totals" in pool_data:
                            key = f"{protocol_name}.{network}.{pool_name}"
                            value = f"{Decimal(pool_data['totals']['formatted']):.6f}"
                            positions[key] = value

    # Process spot positions
    if "spot" in all_balances:
        for network, network_data in all_balances["spot"].items():
            for token_name, token_data in network_data.items():
                if token_name != "totals" and isinstance(token_data, dict):
                    if "totals" in token_data:
                        # Pour les positions spot, on utilise juste network.token_name
                        key = f"{network}.{token_name}"
                        value = f"{Decimal(token_data['totals']['formatted']):.6f}"
                        positions[key] = value

    # Sort positions by value in descending order
    sorted_positions = dict(sorted(
        positions.items(),
        key=lambda x: Decimal(x[1]),
        reverse=True
    ))
    
    # Calculate total value from positions
    total_value = sum(Decimal(value) for value in sorted_positions.values())
    
    # Get total supply from SupplyReader
    supply_reader = SupplyReader(address=address)
    total_supply = supply_reader.format_total_supply()
    
    # Calculate share price
    total_supply_decimal = Decimal(total_supply)
    share_price = total_value / total_supply_decimal if total_supply_decimal != 0 else Decimal('0')
    
    return {
        "nav": {
            "usdc": f"{total_value:.6f}",
            "share_price": f"{share_price:.6f}",
            "total_supply": total_supply
        },
        "positions": {k: f"{Decimal(v):.6f}" for k, v in sorted_positions.items()}
    }

def main():
    """
    Main function to aggregate all balance data.
    Uses command line argument if provided, otherwise uses default address.
    """
    # Default address
    DEFAULT_ADDRESS = '0xc6835323372A4393B90bCc227c58e82D45CE4b7d'
    
    # Get address from command line argument if provided
    address = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ADDRESS
    
    if not Web3.is_address(address):
        print(f"Error: Invalid address format: {address}")
        return None
        
    # Create aggregator and get balances
    aggregator = BalanceAggregator()
    all_balances = aggregator.get_all_balances(address)
    
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
