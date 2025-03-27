import json
from decimal import Decimal
from pathlib import Path
import sys
from typing import Dict, Any
from datetime import datetime, timezone

# Add parent directory to PYTHONPATH
root_path = str(Path(__file__).parent.parent)
sys.path.append(root_path)

from sky.balance_manager import BalanceManager as SkyBalanceManager
from pendle.balance_manager import PendleBalanceManager
from dtusdc.supply_reader import SupplyReader
from balance.usdc_balance_manager import StablecoinBalanceManager

class BalanceAggregator:
    """Aggregates balances from different protocols and spot positions"""
    
    def __init__(self):
        self.sky_manager = SkyBalanceManager()
        self.pendle_manager = PendleBalanceManager()
        self.supply_reader = SupplyReader()
        self.stablecoin_manager = StablecoinBalanceManager()
        
    def get_total_usdc_value(self, address: str) -> Dict[str, Any]:
        # Get current UTC timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        
        # Get protocol positions
        sky_positions = self.sky_manager.get_balances(address)
        pendle_positions = self.pendle_manager.get_balances(address)
        
        # Get spot balances
        spot_balances = self.stablecoin_manager.get_balances(address)
        
        # Calculate total USDC value from protocols
        total_usdc_value = Decimal('0')
        positions_in_usdc = {}
        protocols_value = Decimal('0')  # Ajout d'un compteur spécifique pour les protocoles
        
        # Add Sky positions
        for network, tokens in sky_positions["sky"].items():
            for token, data in tokens.items():
                try:
                    if 'value' in data and 'USDC' in data['value']:
                        usdc_value = Decimal(data['value']['USDC']['amount']) / Decimal(10**6)
                        protocols_value += usdc_value
                        positions_in_usdc[f"sky.{network}.{token}"] = f"{usdc_value:.6f}"
                        print(f"Added Sky position {network}.{token}: {usdc_value:.6f} USDC")
                except (KeyError, TypeError) as e:
                    print(f"Warning: Could not process Sky position for {network}.{token}: {e}")
                    continue

        # Add Pendle positions
        for network, tokens in pendle_positions["pendle"].items():
            for token, data in tokens.items():
                try:
                    if 'value' in data and 'USDC' in data['value']:
                        usdc_value = Decimal(data['value']['USDC']['amount']) / Decimal(10**6)
                        protocols_value += usdc_value
                        positions_in_usdc[f"pendle.{network}.{token}"] = f"{usdc_value:.6f}"
                        print(f"Added Pendle position {network}.{token}: {usdc_value:.6f} USDC")
                except (KeyError, TypeError) as e:
                    print(f"Warning: Could not process Pendle position for {network}.{token}: {e}")
                    continue

        # Add spot balances
        spot_balances_in_usdc = {}
        total_spot_value = Decimal(spot_balances["summary"]["total_usdc_value"])
        total_usdc_value += total_spot_value

        for network, tokens in spot_balances["stablecoins"].items():
            for token, data in tokens.items():
                if token == "USDC":
                    value = Decimal(data["amount"]) / Decimal(10**data["decimals"])
                else:
                    value = Decimal(data["value"]["USDC"]["amount"]) / Decimal(10**6)
                spot_balances_in_usdc[f"spot.{network}.{token}"] = f"{value:.6f}"

        # Get total supply and calculate share price
        total_supply = Decimal(self.supply_reader.get_total_supply()) / Decimal(10**18)
        total_value = protocols_value + total_spot_value
        share_price = total_value / total_supply if total_supply > 0 else Decimal('0')
        
        result = {
            "timestamp": timestamp,
            "nav": {
                "usdc": f"{total_value:.6f}",
                "usdc_wei": str(int(total_value * Decimal(10**6))),
                "share_price": f"{share_price:.6f}",
                "total_supply": str(total_supply)
            },
            "summary": {
                "total_value": f"{total_value:.6f}",
                "protocols_value": f"{protocols_value:.6f}",
                "spot_value": f"{total_spot_value:.6f}"
            },
            "positions_in_usdc": positions_in_usdc,
            "spot_balances_in_usdc": spot_balances_in_usdc,
            "details": {
                "sky": sky_positions,
                "pendle": pendle_positions,
                "spot": spot_balances["stablecoins"]
            }
        }
        
        return result

def main():
    import os
    from dotenv import load_dotenv
    
    # Load environment variables from parent directory
    load_dotenv(Path(root_path) / '.env')
    
    # Get address from command line or .env
    test_address = sys.argv[1] if len(sys.argv) > 1 else os.getenv('DEFAULT_USER_ADDRESS')
    
    if not test_address:
        print("Error: No address provided and DEFAULT_USER_ADDRESS not found in .env")
        sys.exit(1)
    
    print(f"Aggregating balances for {test_address}...")
    aggregator = BalanceAggregator()
    result = aggregator.get_total_usdc_value(test_address)
    print("\nDone! Results:")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main() 