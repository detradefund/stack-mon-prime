import json
from decimal import Decimal
from pathlib import Path
import sys
from typing import Dict, Any
from datetime import datetime, timezone
from web3 import Web3

# Add parent directory to PYTHONPATH
root_path = str(Path(__file__).parent.parent)
sys.path.append(root_path)

from sky.balance_manager import BalanceManager as SkyBalanceManager
from pendle.balance_manager import PendleBalanceManager
from dtusdc.supply_reader import SupplyReader
from balance.usdc_balance_manager import SpotBalanceManager
from convex.balance_manager import ConvexBalanceManager

class BalanceAggregator:
    """
    Aggregates balances from different protocols (Sky, Pendle, Convex) and spot positions.
    Calculates total portfolio value and share price in USDC.
    """
    
    def __init__(self):
        self.sky_manager = SkyBalanceManager()
        self.pendle_manager = PendleBalanceManager()
        self.convex_manager = ConvexBalanceManager()
        self.supply_reader = SupplyReader()
        self.spot_manager = SpotBalanceManager()
        
    def get_total_usdc_value(self, address: str) -> Dict[str, Any]:
        # Convert address to checksum format for consistency
        checksum_address = Web3.to_checksum_address(address)
        
        # Get current UTC timestamp for balance snapshot
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        
        # Fetch positions from all protocols
        sky_positions = self.sky_manager.get_balances(checksum_address)
        pendle_positions = self.pendle_manager.get_balances(checksum_address)
        convex_positions = self.convex_manager.get_balances(checksum_address)
        spot_balances = self.spot_manager.get_balances(checksum_address)
        
        total_usdc_value = Decimal('0')
        positions_in_usdc = {}  # Tracks active positions in DeFi protocols (staking, LP, etc.)
        protocols_value = Decimal('0')  # Total value locked in DeFi protocols (vs spot holdings)
        
        # Process Sky protocol positions
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

        # Process Pendle protocol positions
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

        # Process Convex protocol positions and rewards
        for network, tokens in convex_positions.get("convex", {}).items():
            for token, data in tokens.items():
                try:
                    if data is None:
                        continue
                    # Calculate total value of underlying tokens
                    usdc_value = Decimal('0')
                    
                    # Sum up underlying token values
                    for _, token_data in data['lp_tokens'].items():
                        if token_data.get('decimals') == 6:  # If USDC
                            usdc_value += Decimal(token_data['amount']) / Decimal(10**6)
                        elif 'value' in token_data and 'USDC' in token_data['value']:
                            usdc_value += Decimal(token_data['value']['USDC']['amount']) / Decimal(10**6)
                    
                    # Add rewards value
                    for _, reward_data in data.get('rewards', {}).items():
                        if 'value' in reward_data and 'USDC' in reward_data['value']:
                            usdc_value += Decimal(reward_data['value']['USDC']['amount']) / Decimal(10**6)
                    
                    if usdc_value > 0:
                        protocols_value += usdc_value
                        positions_in_usdc[f"convex.{network}.{token}"] = f"{usdc_value:.6f}"
                except (KeyError, TypeError) as e:
                    print(f"Warning: Could not process Convex position for {network}.{token}: {e}")
                    continue

        # Process spot balances (direct token holdings)
        spot_balances_in_usdc = {}
        total_spot_value = Decimal('0')
        for network, tokens in spot_balances["stablecoins"].items():
            for token, data in tokens.items():
                if token == "USDC":
                    value = Decimal(data["amount"]) / Decimal(10**data["decimals"])
                else:
                    value = Decimal(data["value"]["USDC"]["amount"]) / Decimal(10**6)
                if value > 0:  # N'ajouter que si la valeur est > 0
                    spot_balances_in_usdc[f"spot.{network}.{token}"] = f"{value:.6f}"
                    total_spot_value += value  # Ajouter au total des spots

        # Remove zero balances from detailed position data
        cleaned_sky = {}
        for network, tokens in sky_positions["sky"]["sky"].items():
            cleaned_sky[network] = {}
            for token, data in tokens.items():
                if data is None:
                    continue
                if Decimal(data['value']['USDC']['amount']) > 0:
                    cleaned_sky[network][token] = data

        cleaned_pendle = {}
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

        # Calculate share price based on total value and supply
        total_supply = Decimal(self.supply_reader.get_total_supply()) / Decimal(10**18)
        total_value = protocols_value + total_spot_value
        share_price = total_value / total_supply if total_supply > 0 else Decimal('0')
        
        # Structure final result with portfolio summary and details
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
                "sky": cleaned_sky,
                "pendle": cleaned_pendle,
                "spot": cleaned_spot
            }
        }
        
        # N'ajouter convex aux détails que s'il y a des positions
        if convex_positions and "convex" in convex_positions and convex_positions["convex"]:
            result["details"]["convex"] = convex_positions["convex"]

        return result

def main():
    """
    Command-line interface to test balance aggregation.
    Accepts address as argument or falls back to DEFAULT_USER_ADDRESS from .env
    """
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
    test_address = Web3.to_checksum_address(test_address)
    result = aggregator.get_total_usdc_value(test_address)
    print("\nDone! Results:")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main() 