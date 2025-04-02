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
        
        print(f"\nStarting balance aggregation for {checksum_address}")
        print("=" * 80)
        
        # Get current UTC timestamp for balance snapshot
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        
        # Fetch positions from all protocols
        sky_positions = self.sky_manager.get_balances(checksum_address)
        pendle_positions = self.pendle_manager.get_balances(checksum_address)
        convex_positions = self.convex_manager.get_balances(checksum_address)
        spot_balances = self.spot_manager.get_balances(checksum_address)
        
        total_usdc_value = Decimal('0')
        positions_in_usdc = {}
        protocols_value = Decimal('0')
        total_spot_value = Decimal('0')
        spot_balances_in_usdc = {}
        
        # Process Sky protocol positions
        print("\nChecking Sky Protocol positions...")
        sky_has_positions = False
        if sky_positions["sky"]["sky"]:
            for network, tokens in sky_positions["sky"]["sky"].items():
                network_has_positions = False
                for token, data in tokens.items():
                    try:
                        if data is None:
                            continue
                        if 'value' in data and 'USDC' in data['value']:
                            usdc_value = Decimal(data['value']['USDC']['amount']) / Decimal(10**6)
                            if usdc_value > 0:
                                if not network_has_positions:
                                    print(f"  Network: {network.upper()}")
                                    network_has_positions = True
                                sky_has_positions = True
                                protocols_value += usdc_value
                                positions_in_usdc[f"sky.{network}.{token}"] = f"{usdc_value:.6f}"
                                print(f"    • {token}: {usdc_value:.2f} USDC")
                    except (KeyError, TypeError) as e:
                        print(f"    Warning: Error processing {token}: {e}")
                        continue
        if not sky_has_positions:
            print("  No positions found")
        
        # Process Pendle protocol positions
        print("\nChecking Pendle Protocol positions...")
        pendle_has_positions = False
        if pendle_positions["pendle"]:
            for network in ["ethereum", "base"]:
                network_has_positions = False
                if pendle_positions["pendle"][network]:
                    for token, data in pendle_positions["pendle"][network].items():
                        try:
                            if data is None or not isinstance(data, dict):
                                continue
                            if 'value' in data and 'USDC' in data['value']:
                                usdc_value = Decimal(data['value']['USDC']['amount']) / Decimal(10**6)
                                if usdc_value > 0:
                                    if not network_has_positions:
                                        print(f"  Network: {network.upper()}")
                                        network_has_positions = True
                                    pendle_has_positions = True
                                    protocols_value += usdc_value
                                    positions_in_usdc[f"pendle.{network}.{token}"] = f"{usdc_value:.6f}"
                                    print(f"    • {token}: {usdc_value:.2f} USDC")
                        except (KeyError, TypeError) as e:
                            print(f"    ⚠️  Error processing {token}: {e}")
                            continue
        if not pendle_has_positions:
            print("  No positions found")

        # Process Convex protocol positions
        print("\nChecking Convex Protocol positions...")
        convex_has_positions = False
        if convex_positions.get("convex"):
            cleaned_convex = {}
            for network, tokens in convex_positions.get("convex", {}).items():
                network_has_positions = False
                cleaned_convex[network] = {}
                for token, data in tokens.items():
                    try:
                        if data is None:
                            continue
                        usdc_value = Decimal('0')
                        
                        # Sum up underlying token values
                        for token_name, token_data in data['lp_tokens'].items():
                            token_value = (Decimal(token_data['amount']) / Decimal(10**6) if token_data.get('decimals') == 6
                                         else Decimal(token_data['value']['USDC']['amount']) / Decimal(10**6)
                                         if 'value' in token_data and 'USDC' in token_data['value'] else Decimal('0'))
                            usdc_value += token_value
                        
                        # Add rewards value
                        for reward_name, reward_data in data.get('rewards', {}).items():
                            if 'value' in reward_data and 'USDC' in reward_data['value']:
                                reward_value = Decimal(reward_data['value']['USDC']['amount']) / Decimal(10**6)
                                usdc_value += reward_value
                        
                        if usdc_value > 0:
                            if not network_has_positions:
                                print(f"  Network: {network.upper()}")
                                network_has_positions = True
                            convex_has_positions = True
                            protocols_value += usdc_value
                            positions_in_usdc[f"convex.{network}.{token}"] = f"{usdc_value:.6f}"
                            cleaned_convex[network][token] = convex_positions["convex"][network][token]
                            print(f"    • {token}: {usdc_value:.2f} USDC")
                    except (KeyError, TypeError) as e:
                        print(f"    ⚠️  Error processing {token}: {e}")
                        continue
        if not convex_has_positions:
            print("  No positions found")

        # Process spot balances
        print("\nChecking Spot balances...")
        spot_has_balances = False
        if any(tokens for tokens in spot_balances["stablecoins"].values()):
            for network, tokens in spot_balances["stablecoins"].items():
                network_has_balances = False
                for token, data in tokens.items():
                    value = (Decimal(data["amount"]) / Decimal(10**data["decimals"]) if token == "USDC"
                            else Decimal(data["value"]["USDC"]["amount"]) / Decimal(10**6))
                    if value > 0:
                        if not network_has_balances:
                            print(f"  Network: {network.upper()}")
                            network_has_balances = True
                        spot_has_balances = True
                        spot_balances_in_usdc[f"spot.{network}.{token}"] = f"{value:.6f}"
                        total_spot_value += value
                        print(f"    • {token}: {value:.2f} USDC")
        if not spot_has_balances:
            print("  No balances found")

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
        
        print("\nPortfolio Summary")
        print("=" * 80)
        print(f"Total Portfolio Value: {total_value:.2f} USDC")
        print(f"  • Protocol Positions: {protocols_value:.2f} USDC")
        print(f"  • Spot Balances: {total_spot_value:.2f} USDC")
        print(f"Share Price: {share_price:.6f} USDC")
        print("=" * 80 + "\n")

        # Structure final result with portfolio summary and details
        details = {}
        
        # Only add protocols with positions
        if sky_has_positions:
            details["sky"] = sky_positions["sky"]["sky"]
            
        if pendle_positions["pendle"]:
            details["pendle"] = pendle_positions["pendle"]
            
        if convex_positions.get("convex"):
            details["convex"] = convex_positions["convex"]
            
        if any(tokens for tokens in cleaned_spot.values()):
            details["spot"] = cleaned_spot

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
            "details": details
        }
        
        return result

def main():
    """
    Command-line interface to test balance aggregation.
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
    
    aggregator = BalanceAggregator()
    test_address = Web3.to_checksum_address(test_address)
    result = aggregator.get_total_usdc_value(test_address)
    
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main() 