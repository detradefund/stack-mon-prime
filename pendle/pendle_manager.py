"""
Master script to manage Pendle positions, balances, and conversions.
"""
import json
from pathlib import Path
from typing import Dict, List, Optional
from decimal import Decimal
from web3 import Web3
import sys
from datetime import datetime
import os
from dotenv import load_dotenv

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from config.networks import RPC_URLS
from pendle.balance.check_balances import get_pt_balances, get_pendle_lp_balances
from pendle.sdk.convert_pt import convert_pt
from pendle.sdk.remove_liquidity import remove_liquidity
from pendle.markets.pendle_markets import PendleMarkets

# Load environment variables
load_dotenv()

def format_amount(wei_str):
    """Format wei amount to ETH with 6 decimals."""
    eth = int(wei_str) / 1e18
    return f"{eth:,.6f}"

class PendleManager:
    def __init__(self, wallet_address: str):
        """
        Initialize the PendleManager.
        
        Args:
            wallet_address: The wallet address to manage positions for
        """
        self.wallet_address = wallet_address
        self.markets_manager = PendleMarkets()
        self.positions = {}
        
    def refresh_market_data(self):
        """Refresh all market data and update market mapping."""
        print("\n=== Refreshing Market Data ===")
        self.markets_manager.refresh_all_markets()
        self.markets_manager.fetch_active_markets()
        self.markets_manager.create_market_mapping()
        print("✓ Market data refreshed successfully")
        
    def check_balances(self):
        """Check all PT and LP token balances across all networks."""
        print("\n=== Checking Balances ===")
        self.positions = {}
        
        # Check balances on each network
        for network, rpc_url in RPC_URLS.items():
            print(f"\nNetwork: {network}")
            w3 = Web3(Web3.HTTPProvider(rpc_url))
            chain_id = "1" if network == "ethereum" else "8453" if network == "base" else None
            
            if chain_id is None:
                print(f"⚠️ Unsupported network: {network}")
                continue
                
            # Get PT balances
            pt_balances = get_pt_balances(w3, self.wallet_address, chain_id)
            for market_address, balance_data in pt_balances.items():
                if balance_data["balance"] > 0:
                    if market_address not in self.positions:
                        self.positions[market_address] = {"pt": balance_data, "lp": Decimal('0')}
                    else:
                        self.positions[market_address]["pt"] = balance_data
                    print(f"✓ Found {balance_data['balance']} {balance_data['token']['symbol']} tokens in market {balance_data['market']}")
            
            # Get LP balances
            lp_balances = get_pendle_lp_balances(w3, self.wallet_address, chain_id)
            for market_address, balance in lp_balances.items():
                if balance > 0:
                    if market_address not in self.positions:
                        self.positions[market_address] = {"pt": {"balance": Decimal('0')}, "lp": balance}
                    else:
                        self.positions[market_address]["lp"] = balance
                    print(f"✓ Found {balance} LP tokens in market {market_address}")
        
        # Print summary of positions found
        if self.positions:
            print("\n=== Positions Found ===")
            for market_address, balances in self.positions.items():
                market_name = balances['pt'].get('market', market_address) if 'pt' in balances else market_address
                print(f"\nMarket: {market_name}")
                if 'pt' in balances and balances["pt"]["balance"] > 0:
                    print(f"  PT Balance: {balances['pt']['balance']} {balances['pt']['token']['symbol']}")
                if balances["lp"] > 0:
                    print(f"  LP Balance: {balances['lp']}")
        else:
            print("\n⚠️ No positions found")
        
        return self.positions
        
    def process_positions(self, slippage: float = 0.05):
        """
        Process all positions by converting PT tokens and removing liquidity.
        
        Args:
            slippage: Maximum acceptable slippage (default: 0.05 = 5%)
            
        Returns:
            dict: Dictionary containing all positions and totals
        """
        if not self.positions:
            print("\n⚠️ No positions found to process")
            return None
            
        print("\n=== Processing Positions ===")
        
        # Data structure to store all results
        results = {
            "ethereum": {},
            "base": {}
        }
        
        # Process each position
        for market_address, position_data in self.positions.items():
            network = "ethereum" if market_address.startswith("0x") else "base"
            print(f"\nProcessing market: {market_address}")
            
            # Process PT tokens
            if position_data["pt"]["balance"] > 0:
                try:
                    pt_result = convert_pt(
                        market_address=market_address,
                        amount=int(position_data["pt"]["balance"] * Decimal('1e18')),  # Convert to wei
                        receiver=self.wallet_address,
                        slippage=slippage
                    )
                    
                    # Extract conversion details
                    conversion_details = None
                    weth_amount = "0"
                    if pt_result["best_amount"]:
                        weth_amount = str(int(float(pt_result["best_amount"].replace(",", "")) * 1e18))
                        best_method = pt_result["best_method"]
                        method_data = pt_result["methods"][best_method]
                        
                        if method_data["success"]:
                            steps = method_data["steps"]
                            last_step = steps[-1]
                            conversion_details = {
                                "source": "Pendle SDK",
                                "price_impact": last_step.get("price_impact", "0.0000").replace("%", ""),
                                "rate": str(Decimal(weth_amount) / (position_data["pt"]["balance"] * Decimal('1e18'))),
                                "fee_percentage": "0.0000%",
                                "fallback": False,
                                "note": "Direct Conversion using Pendle SDK"
                            }
                    
                    # Create entry for this market
                    token_symbol = position_data["pt"]["token"]["symbol"]
                    results[network][token_symbol] = {
                        "amount": str(int(position_data["pt"]["balance"] * Decimal('1e18'))),
                        "decimals": position_data["pt"]["token"]["decimals"],
                        "token": {
                            "address": position_data["pt"]["token"]["address"],
                            "symbol": position_data["pt"]["token"]["symbol"],
                            "name": position_data["pt"]["token"]["name"]
                        },
                        "market": position_data["pt"]["market"],
                        "market_address": market_address,
                        "value": {
                            "WETH": {
                                "amount": weth_amount,
                                "decimals": 18,
                                "conversion_details": conversion_details
                            }
                        },
                        "totals": {
                            "wei": weth_amount,
                            "formatted": format_amount(weth_amount)
                        }
                    }
                    
                except Exception as e:
                    print(f"✗ Error converting PT tokens: {str(e)}")
            
            # Process LP tokens
            if position_data["lp"] > 0:
                try:
                    lp_result = remove_liquidity(
                        market_address=market_address,
                        amount=int(position_data["lp"] * Decimal('1e18')),  # Convert to wei
                        receiver=self.wallet_address,
                        slippage=slippage
                    )
                except Exception as e:
                    print(f"✗ Error removing liquidity: {str(e)}")
        
        # Calculate totals at the end
        network_totals = {}
        global_total = Decimal('0')
        
        for network in ["ethereum", "base"]:
            if network in results:
                network_total = Decimal('0')
                for token_data in results[network].values():
                    if "totals" in token_data:
                        network_total += Decimal(token_data["totals"]["wei"])
                
                if network_total > 0:
                    network_totals[network] = {
                        "wei": str(network_total),
                        "formatted": format_amount(str(network_total))
                    }
                    global_total += network_total
        
        # Add totals to result
        for network, total in network_totals.items():
            results[network]["totals"] = total
        
        if global_total > 0:
            results["totals"] = {
                "wei": str(global_total),
                "formatted": format_amount(str(global_total))
            }
        
        # Clean up empty networks
        for network in ["ethereum", "base"]:
            if network in results and not results[network]:
                del results[network]
        
        return results
    
    def run(self, refresh_markets: bool = True, slippage: float = 0.05):
        """
        Run the complete process.
        
        Args:
            refresh_markets: Whether to refresh market data before processing (default: True)
            slippage: Maximum acceptable slippage (default: 0.05 = 5%)
            
        Returns:
            dict: Complete processing results including positions and totals
        """
        print("\n=== Pendle Position Manager ===")
        print(f"Wallet: {self.wallet_address}")
        print(f"Time: {datetime.now().isoformat()}")
        
        if refresh_markets:
            self.refresh_market_data()
        
        self.check_balances()
        results = self.process_positions(slippage)
        
        print("\n=== Process Complete ===")
        return results

def main():
    """Example usage of the PendleManager."""
    # Get production address from .env
    production_address = os.getenv('PRODUCTION_ADDRESS')
    if not production_address:
        raise ValueError("PRODUCTION_ADDRESS not found in .env file")
    
    try:
        print("\n=== Testing with Production Address ===")
        manager = PendleManager(production_address)
        results = manager.run()

        # Display results
        print("\n=== Results ===")
        print(json.dumps(results, indent=2))
        
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        print("\nFull error traceback:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 