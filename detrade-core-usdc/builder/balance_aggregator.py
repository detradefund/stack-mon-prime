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
        for network, tokens in sky_positions["sky"]["sky"].items():
            for token, data in tokens.items():
                try:
                    if data is None:
                        continue
                    if 'value' in data and 'USDC' in data['value']:
                        usdc_value = Decimal(data['value']['USDC']['amount']) / Decimal(10**6)
                        if usdc_value > 0:
                            protocols_value += usdc_value
                            positions_in_usdc[f"sky.{network}.{token}"] = f"{usdc_value:.6f}"
                except (KeyError, TypeError) as e:
                    print(f"Warning: Could not process Sky position for {network}.{token}: {e}")
                    continue

        # Add Pendle positions
        for network, tokens in pendle_positions["pendle"].items():
            for token, data in tokens.items():
                try:
                    if data is None or not isinstance(data, dict):
                        continue
                    if 'value' in data and 'USDC' in data['value']:
                        usdc_value = Decimal(data['value']['USDC']['amount']) / Decimal(10**6)
                        if usdc_value > 0:
                            protocols_value += usdc_value
                            positions_in_usdc[f"pendle.{network}.{token}"] = f"{usdc_value:.6f}"
                except (KeyError, TypeError) as e:
                    print(f"Warning: Could not process Pendle position for {network}.{token}: {e}")
                    continue

        # Add spot balances
        spot_balances_in_usdc = {}
        total_spot_value = Decimal('0')  # Initialiser le total des spots
        for network, tokens in spot_balances["stablecoins"].items():
            for token, data in tokens.items():
                if token == "USDC":
                    value = Decimal(data["amount"]) / Decimal(10**data["decimals"])
                else:
                    value = Decimal(data["value"]["USDC"]["amount"]) / Decimal(10**6)
                if value > 0:  # N'ajouter que si la valeur est > 0
                    spot_balances_in_usdc[f"spot.{network}.{token}"] = f"{value:.6f}"
                    total_spot_value += value  # Ajouter au total des spots

        # Clean up details to remove zero balances
        cleaned_sky = {}  # Plus de niveau "sky" du tout
        for network, tokens in sky_positions["sky"]["sky"].items():
            cleaned_sky[network] = {}
            for token, data in tokens.items():
                if data is None:
                    continue
                if Decimal(data['value']['USDC']['amount']) > 0:
                    cleaned_sky[network][token] = data

        cleaned_pendle = {}  # Plus de niveau "pendle" du tout
        for network, tokens in pendle_positions["pendle"].items():
            cleaned_pendle[network] = {}
            for token, data in tokens.items():
                if data is None:
                    continue
                if Decimal(data['value']['USDC']['amount']) > 0:
                    cleaned_pendle[network][token] = data

        cleaned_spot = {}
        for network, tokens in spot_balances["stablecoins"].items():
            cleaned_spot[network] = {}
            for token, data in tokens.items():
                value = Decimal(data["amount"]) if token == "USDC" else Decimal(data["value"]["USDC"]["amount"])
                if value > 0:
                    cleaned_spot[network][token] = data

        # Get total supply and calculate share price
        total_supply = Decimal(self.supply_reader.get_total_supply()) / Decimal(10**18)
        total_value = protocols_value + total_spot_value  # Utiliser total_spot_value au lieu de total_usdc_value
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
                "spot_value": f"{total_spot_value:.6f}"  # Utiliser total_spot_value
            },
            "positions_in_usdc": positions_in_usdc,
            "spot_balances_in_usdc": spot_balances_in_usdc,
            "details": {
                "sky": cleaned_sky,    # Sera directement {network: {token: data}}
                "pendle": cleaned_pendle,  # Sera directement {network: {token: data}}
                "spot": cleaned_spot
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