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

class BalanceAggregator:
    """Aggregates balances from different protocols"""
    
    def __init__(self):
        self.sky_manager = SkyBalanceManager()
        self.pendle_manager = PendleBalanceManager()
        self.supply_reader = SupplyReader()
        
    def get_total_usdc_value(self, address: str) -> Dict[str, Any]:
        # Get current UTC timestamp
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        
        result = {
            "timestamp": timestamp,
            "nav": {  # Net Asset Value
                "usdc": "0",
                "usdc_wei": "0"
            },
            "positions_in_usdc": {},
            "details": {}
        }
        
        # Get Sky balances
        print("\n=== Fetching Sky positions ===")
        sky_balances = self.sky_manager.get_balances(address)
        
        # Calculate totals
        sky_usdc_total = Decimal('0')
        sky_summary = {}
        
        print("\nSky Positions Breakdown:")
        print("------------------------")
        for network, tokens in sky_balances.get('sky', {}).items():
            network_total = Decimal('0')
            for token_symbol, token_data in tokens.items():
                usdc_value = Decimal(token_data['value']['USDC']['amount'])
                network_total += usdc_value
                sky_usdc_total += usdc_value
                if usdc_value > 0:
                    position_key = f"sky.{network}.{token_symbol}"
                    sky_summary[position_key] = f"{usdc_value/Decimal('1000000'):.6f}"
                    print(f"  {network:10} | {token_symbol:15} | {usdc_value/Decimal('1000000'):,.2f} USDC")
            if network_total > 0:
                print(f"  {network:10} Total: {network_total/Decimal('1000000'):,.2f} USDC")
                print("  " + "-" * 45)
        
        print(f"\nSky Total: {sky_usdc_total/Decimal('1000000'):,.2f} USDC")
        
        # Get Pendle balances
        print("\n=== Fetching Pendle positions ===")
        pendle_balances = self.pendle_manager.get_balances(address)
        
        pendle_usdc_total = Decimal('0')
        pendle_summary = {}
        
        print("\nPendle Positions Breakdown:")
        print("--------------------------")
        for network, tokens in pendle_balances.get('pendle', {}).items():
            network_total = Decimal('0')
            for token_symbol, token_data in tokens.items():
                usdc_value = Decimal(token_data['value']['USDC']['amount'])
                network_total += usdc_value
                pendle_usdc_total += usdc_value
                if usdc_value > 0:
                    position_key = f"pendle.{network}.{token_symbol}"
                    pendle_summary[position_key] = f"{usdc_value/Decimal('1000000'):.6f}"
                    print(f"  {network:10} | {token_symbol:15} | {usdc_value/Decimal('1000000'):,.2f} USDC")
            if network_total > 0:
                print(f"  {network:10} Total: {network_total/Decimal('1000000'):,.2f} USDC")
                print("  " + "-" * 45)
        
        print(f"\nPendle Total: {pendle_usdc_total/Decimal('1000000'):,.2f} USDC")
        
        print("\n=== Computing totals ===")
        total_usdc_wei = sky_usdc_total + pendle_usdc_total
        total_usdc = total_usdc_wei / Decimal('1000000')
        print(f"Total Value: {total_usdc:,.2f} USDC")
        
        # Calculate share price (silently)
        total_supply = Decimal(self.supply_reader.get_total_supply())
        formatted_supply = self.supply_reader.format_total_supply()
        
        if total_supply > 0:
            # total_supply is in 10^18
            # total_usdc_wei is in 10^6
            adjusted_usdc = total_usdc_wei * Decimal('1000000000000')  # Ajout de 12 zéros
            share_price_wei = (adjusted_usdc * Decimal('1000000')) // total_supply
            share_price = share_price_wei / Decimal('1000000')
            
            result["nav"].update({
                "share_price": f"{share_price:.6f}",
                "total_supply": formatted_supply
            })
        
        # Build response
        result["nav"]["usdc"] = f"{total_usdc:.6f}"
        result["nav"]["usdc_wei"] = str(total_usdc_wei)
        result["positions_in_usdc"] = {**sky_summary, **pendle_summary}
        result["details"] = {
            "sky": sky_balances["sky"],
            "pendle": pendle_balances["pendle"]
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