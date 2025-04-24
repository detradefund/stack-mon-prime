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
        total_usdc = 0
        
        # Get pendle balances
        try:
            pendle_balances = self.pendle_manager.get_balances(checksum_address)
            if pendle_balances:
                result.update(pendle_balances)
                if "pendle" in pendle_balances and "usdc_totals" in pendle_balances["pendle"]:
                    total_usdc += int(pendle_balances["pendle"]["usdc_totals"]["total"]["wei"])
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

        # Get Equilibria balances
        try:
            equilibria_balances = self.equilibria_manager.get_balances(checksum_address)
            # Check if we have a non-zero balance before adding to result
            if (equilibria_balances and 
                "equilibria" in equilibria_balances and 
                "ethereum" in equilibria_balances["equilibria"] and
                "GHO-USR" in equilibria_balances["equilibria"]["ethereum"] and
                int(equilibria_balances["equilibria"]["ethereum"]["GHO-USR"]["amount"]) > 0):
                
                result.update(equilibria_balances)
                chain_data = equilibria_balances["equilibria"]["ethereum"]
                if "GHO-USR" in chain_data:
                    total_usdc += int(chain_data["GHO-USR"]["usdc_totals"]["total"]["wei"])
                print("✓ Equilibria positions fetched successfully")
        except Exception as e:
            print(f"✗ Error fetching Equilibria positions: {str(e)}")
        
        # Get Tokemak balances
        try:
            tokemak_balances = self.tokemak_manager.get_balances(checksum_address)
            if tokemak_balances:
                result.update(tokemak_balances)
                if "tokemak" in tokemak_balances:
                    chain_data = tokemak_balances["tokemak"]["ethereum"]
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
            spot_balances = {
                "spot": {
                    "usdc_totals": {
                        "total": {
                            "wei": 0,
                            "formatted": "0.000000"
                        }
                    }
                }
            }

        # Add global USDC total across PROTOCOLS ONLY (not including spot)
        result["usdc_totals"] = {
            "total": {
                "wei": total_usdc,
                "formatted": f"{total_usdc/1e6:.2f}"
            }
        }
        
        # Create a sorted list of protocols based on their USDC totals
        protocol_totals = []

        # Add each protocol with its total
        for protocol_name, protocol_data in result.items():
            if protocol_name != "usdc_totals":
                if "usdc_totals" in protocol_data:
                    # Pour les protocoles avec un total global direct (Sky, Pendle)
                    protocol_totals.append(
                        (protocol_name, int(protocol_data["usdc_totals"]["total"]["wei"]))
                    )
                elif protocol_name in ["convex", "equilibria"]:
                    # Pour les protocoles avec des pools
                    total = sum(
                        int(pool_data["usdc_totals"]["total"]["wei"])
                        for chain_data in protocol_data.values()
                        for pool_data in chain_data.values()
                        if isinstance(pool_data, dict) and "usdc_totals" in pool_data
                    )
                    protocol_totals.append((protocol_name, total))
                elif protocol_name == "tokemak" and "ethereum" in protocol_data:
                    # Pour Tokemak qui a une structure spécifique
                    if "usdc_totals" in protocol_data["ethereum"]:
                        protocol_totals.append(
                            (protocol_name, int(protocol_data["ethereum"]["usdc_totals"]["total"]["wei"]))
                        )

        # Sort protocols by USDC value in descending order
        protocol_totals.sort(key=lambda x: x[1], reverse=True)

        # Create new ordered dictionary with sorted protocols
        ordered_balances = {}
        for protocol, total in protocol_totals:
            ordered_balances[protocol] = result[protocol]

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
    
    # Initialize positions dictionary
    positions = {}
    
    # Process each protocol's positions
    for protocol_name, protocol_data in all_balances["protocols"].items():
        if protocol_name == "usdc_totals":
            continue
            
        for network, network_data in protocol_data.items():
            if network == "usdc_totals":
                continue
                
            # For Sky
            if protocol_name == "sky":
                for token_name, token_data in network_data.items():
                    if token_name != "usdc_totals" and isinstance(token_data, dict):
                        key = f"{protocol_name}.{network}.{token_name}"
                        value = f"{Decimal(token_data['value']['USDC']['amount']) / Decimal(1e6):.6f}"
                        positions[key] = value
            
            # For Pendle
            elif protocol_name == "pendle":
                for token_name, token_data in network_data.items():
                    if token_name != "usdc_totals" and isinstance(token_data, dict):
                        key = f"{protocol_name}.{network}.{token_name}"
                        value = f"{Decimal(token_data['value']['USDC']['amount']) / Decimal(1e6):.6f}"
                        positions[key] = value
            
            # For Convex
            elif protocol_name == "convex":
                for pool_name, pool_data in network_data.items():
                    if pool_name != "usdc_totals" and isinstance(pool_data, dict):
                        # Calculate total by adding USDC values of LP tokens and rewards
                        pool_total = Decimal('0')
                        
                        # Add USDC values of LP tokens
                        if "lp_tokens" in pool_data:
                            for token_data in pool_data["lp_tokens"].values():
                                if "value" in token_data and "USDC" in token_data["value"]:
                                    pool_total += Decimal(token_data["value"]["USDC"]["amount"]) / Decimal(1e6)
                        
                        # Add USDC values of rewards
                        if "rewards" in pool_data:
                            for token_data in pool_data["rewards"].values():
                                if "value" in token_data and "USDC" in token_data["value"]:
                                    pool_total += Decimal(token_data["value"]["USDC"]["amount"]) / Decimal(1e6)
                        
                        # Add entry if pool has value
                        if pool_total > 0:
                            key = f"{protocol_name}.{network}.{pool_name}"
                            value = f"{pool_total:.6f}"
                            positions[key] = value

            # For Equilibria
            elif protocol_name == "equilibria":
                for pool_name, pool_data in network_data.items():
                    if pool_name != "usdc_totals" and isinstance(pool_data, dict):
                        pool_total = 0
                        
                        # Add main pool value
                        if "value" in pool_data and "USDC" in pool_data["value"]:
                            pool_total += int(pool_data["value"]["USDC"]["amount"])
                        
                        # Add reward values
                        if "rewards" in pool_data:
                            for token_name, token_data in pool_data["rewards"].items():
                                if isinstance(token_data, dict) and "value" in token_data and "USDC" in token_data["value"]:
                                    pool_total += int(token_data["value"]["USDC"]["amount"])
                        
                        # Add entry if pool has value
                        if pool_total > 0:
                            key = f"{protocol_name}.{network}.{pool_name}"
                            value = str(Decimal(pool_total) / Decimal(1e6))
                            positions[key] = value

            # For Tokemak
            elif protocol_name == "tokemak":
                for pool_name, pool_data in network_data.items():
                    if pool_name != "usdc_totals" and isinstance(pool_data, dict):
                        # If it's a main pool (not rewards)
                        if pool_name != "rewards":
                            pool_total = Decimal('0')
                            
                            # Add main USDC value of the pool
                            if "value" in pool_data and "USDC" in pool_data["value"]:
                                pool_total += Decimal(pool_data["value"]["USDC"]["amount"]) / Decimal(1e6)
                            
                            # Add rewards at network level
                            if "rewards" in network_data:
                                for reward_name, reward_data in network_data["rewards"].items():
                                    if "value" in reward_data and "USDC" in reward_data["value"]:
                                        pool_total += Decimal(reward_data["value"]["USDC"]["amount"]) / Decimal(1e6)
                            
                            # Add entry if pool has value
                            if pool_total > 0:
                                key = f"{protocol_name}.{network}.{pool_name}"
                                value = f"{pool_total:.6f}"
                                positions[key] = value

    # Sort positions by value in descending order
    sorted_positions = dict(sorted(
        positions.items(),
        key=lambda x: Decimal(x[1]),
        reverse=True
    ))
    
    # Calculate protocols_value from positions
    protocols_value = sum(Decimal(value) for value in sorted_positions.values())
    
    # Calculate other values
    spot_value = Decimal(all_balances["spot"]["usdc_totals"]["total"]["formatted"])
    total_value = protocols_value + spot_value
    
    # Get total supply from SupplyReader
    supply_reader = SupplyReader()
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
        "overview": {
            "summary": {
                "total_value_usdc": f"{total_value:.6f}",
                "protocols_value_usdc": f"{protocols_value:.6f}",
                "spot_value_usdc": f"{spot_value:.6f}"
            },
            "positions": {k: f"{Decimal(v):.6f}" for k, v in sorted_positions.items()}
        }
    }

def main():
    """CLI utility for testing balance aggregation."""
    from dotenv import load_dotenv
    import os
    from datetime import datetime, timezone
    
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
    
    # Build the final result with overview, protocols and spot sections
    overview = build_overview(all_balances)
    
    # Format created_at to match timestamp format
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    
    final_result = {
        **overview,  # Add overview at the top
        "protocols": all_balances["protocols"],
        "spot": all_balances["spot"],
        "address": test_address,
        "created_at": created_at
    }
    
    # Display final result
    print("\n" + "="*80)
    print("FINAL AGGREGATED RESULT")
    print("="*80 + "\n")
    print(json.dumps(final_result, indent=2))
    
    return final_result

if __name__ == "__main__":
    results = main()
