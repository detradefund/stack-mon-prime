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
from tokemak.balance_manager import BalanceManager as TokemakBalanceManager
from spot.balance_manager import SpotBalanceManager
from convex.balance_manager import ConvexBalanceManager
from shares.supply_reader import SupplyReader

class BalanceAggregator:
    """
    Master aggregator that combines balances from multiple protocols.
    Currently supports:
    - Pendle (Ethereum + Base)
    - Tokemak (Ethereum)
    - Spot (Ethereum + Base)
    - Convex (Ethereum)
    """
    
    def __init__(self):
        self.pendle_manager = PendleBalanceManager()
        self.tokemak_manager = TokemakBalanceManager()
        self.spot_manager = SpotBalanceManager()
        self.convex_manager = ConvexBalanceManager()
        
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
        
        # Initialize result structure
        result = {
            "protocols": {
                "pendle": {},
                "tokemak": {},
                "convex": {}
            },
            "spot": {}
        }
        
        # Get pendle balances
        try:
            pendle_balances = self.pendle_manager.get_balances(checksum_address)
            if pendle_balances:
                result["protocols"]["pendle"] = pendle_balances.get("pendle", {})
                print("✓ Pendle positions fetched successfully")
        except Exception as e:
            print(f"✗ Error fetching Pendle positions: {str(e)}")
        
        # Get Tokemak balances
        try:
            tokemak_balances = self.tokemak_manager.get_balances(checksum_address)
            if tokemak_balances:
                result["protocols"]["tokemak"] = tokemak_balances.get("tokemak", {})
                print("✓ Tokemak positions fetched successfully")
        except Exception as e:
            print(f"✗ Error fetching Tokemak positions: {str(e)}")
            
        # Get Convex balances
        try:
            convex_balances = self.convex_manager.get_balances(checksum_address)
            if convex_balances:
                result["protocols"]["convex"] = convex_balances.get("convex", {})
                print("✓ Convex positions fetched successfully")
        except Exception as e:
            print(f"✗ Error fetching Convex positions: {str(e)}")
        
        # Get spot balances
        try:
            spot_balances = self.spot_manager.get_balances(checksum_address)
            if spot_balances:
                result["spot"] = spot_balances
                print("✓ Spot positions fetched successfully")
        except Exception as e:
            print(f"✗ Error fetching Spot positions: {str(e)}")
            # Initialize empty spot structure
            result["spot"] = {
                "ethereum": {
                    "WETH": {
                        "amount": "0",
                        "decimals": 18,
                        "value": {
                            "USDC": {
                                "amount": "0",
                                "decimals": 6,
                                "conversion_details": {
                                    "source": "Direct",
                                    "price_impact": "0.0000%",
                                    "rate": "0",
                                    "fee_percentage": "0.0000%",
                                    "fallback": False,
                                    "note": "Error fetching balances"
                                }
                            }
                        }
                    },
                    "USDC": {
                        "amount": "0",
                        "decimals": 6,
                        "value": {
                            "USDC": {
                                "amount": "0",
                                "decimals": 6,
                                "conversion_details": {
                                    "source": "Direct",
                                    "price_impact": "0.0000%",
                                    "rate": "0",
                                    "fee_percentage": "0.0000%",
                                    "fallback": False,
                                    "note": "Error fetching balances"
                                }
                            }
                        }
                    },
                    "PENDLE": {
                        "amount": "0",
                        "decimals": 18,
                        "value": {
                            "USDC": {
                                "amount": "0",
                                "decimals": 6,
                                "conversion_details": {
                                    "source": "Direct",
                                    "price_impact": "0.0000%",
                                    "rate": "0",
                                    "fee_percentage": "0.0000%",
                                    "fallback": False,
                                    "note": "Error fetching balances"
                                }
                            }
                        }
                    },
                    "totals": {
                        "wei": 0,
                        "formatted": "0.000000"
                    }
                },
                "base": {
                    "WETH": {
                        "amount": "0",
                        "decimals": 18,
                        "value": {
                            "USDC": {
                                "amount": "0",
                                "decimals": 6,
                                "conversion_details": {
                                    "source": "Direct",
                                    "price_impact": "0.0000%",
                                    "rate": "0",
                                    "fee_percentage": "0.0000%",
                                    "fallback": False,
                                    "note": "Error fetching balances"
                                }
                            }
                        }
                    },
                    "USDC": {
                        "amount": "0",
                        "decimals": 6,
                        "value": {
                            "USDC": {
                                "amount": "0",
                                "decimals": 6,
                                "conversion_details": {
                                    "source": "Direct",
                                    "price_impact": "0.0000%",
                                    "rate": "0",
                                    "fee_percentage": "0.0000%",
                                    "fallback": False,
                                    "note": "Error fetching balances"
                                }
                            }
                        }
                    },
                    "totals": {
                        "wei": 0,
                        "formatted": "0.000000"
                    }
                },
                "totals": {
                    "wei": 0,
                    "formatted": "0.000000"
                }
            }
        
        return result

def build_overview(all_balances: Dict[str, Any], address: str) -> Dict[str, Any]:
    """Build overview section with positions"""
    
    # Initialize positions dictionary
    positions = {}
    
    # Process each protocol's positions
    for protocol_name, protocol_data in all_balances["protocols"].items():
        # For protocols with direct totals (Pendle, Tokemak, Convex)
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

    # Process spot positions
    if "spot" in all_balances:
        for network, network_data in all_balances["spot"].items():
            for token_name, token_data in network_data.items():
                if token_name != "totals" and isinstance(token_data, dict):
                    if "value" in token_data and "WETH" in token_data["value"]:
                        key = f"{network}.{token_name}"
                        value = f"{Decimal(token_data['value']['WETH']['amount']) / Decimal(10**18):.6f}"
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
            "weth": f"{total_value:.6f}",
            "share_price": f"{share_price:.6f}",
            "total_supply": total_supply
        },
        "positions": sorted_positions
    }

def main():
    """
    Main function to aggregate all balance data.
    Uses command line argument if provided, otherwise uses default address.
    """
    # Default address
    DEFAULT_ADDRESS = '0x66DbceE7feA3287B3356227d6F3DfF3CeFbC6F3C'
    
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
