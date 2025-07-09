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
import time
import requests
from dotenv import load_dotenv

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from config.networks import RPC_URLS
from pendle.balance.check_balances import get_pt_balances, get_pendle_lp_balances
from pendle.sdk.convert_pt import convert_pt
from pendle.sdk.remove_liquidity import remove_liquidity
from pendle.markets.pendle_markets import PendleMarkets
from utils.retry import APIRetry

# Load environment variables
load_dotenv()

# Aggregator configuration with computing unit costs
AGGREGATORS = {
    "kyberswap": {"cost": 5, "name": "kyberswap"},
    "odos": {"cost": 15, "name": "odos"},
    "paraswap": {"cost": 15, "name": "paraswap"}
}

# Rate limiting configuration
RATE_LIMIT_CONFIG = {
    "max_units_per_minute": 100,
    "total_cost_per_quote": sum(agg["cost"] for agg in AGGREGATORS.values()),  # 35 units
    "delay_between_aggregators": 2,  # seconds between each aggregator call
    "delay_between_quotes": 20  # seconds between quote batches
}

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
        
        # Rate limiting tracking
        self.last_quote_time = 0
        self.computing_units_used = 0
        self.minute_start_time = time.time()
        
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
        
    def _manage_rate_limit(self):
        """Manage rate limiting for computing units."""
        current_time = time.time()
        
        # Reset counter if a minute has passed
        if current_time - self.minute_start_time >= 60:
            self.computing_units_used = 0
            self.minute_start_time = current_time
            print("\n[Rate Limit] Reset: New minute started")
        
        # Check if we need to wait before next quote batch
        total_cost = RATE_LIMIT_CONFIG["total_cost_per_quote"]
        if self.computing_units_used + total_cost > RATE_LIMIT_CONFIG["max_units_per_minute"]:
            wait_time = 60 - (current_time - self.minute_start_time)
            if wait_time > 0:
                print(f"\n[Rate Limit] Waiting {wait_time:.1f}s (used {self.computing_units_used}/{RATE_LIMIT_CONFIG['max_units_per_minute']} units)")
                time.sleep(wait_time)
                self.computing_units_used = 0
                self.minute_start_time = time.time()
        
        # Add delay between quote batches
        if self.last_quote_time > 0:
            time_since_last = current_time - self.last_quote_time
            min_delay = RATE_LIMIT_CONFIG["delay_between_quotes"]
            if time_since_last < min_delay:
                wait_time = min_delay - time_since_last
                print(f"\n[Rate Limit] Quote spacing: waiting {wait_time:.1f}s")
                time.sleep(wait_time)
        
    def _get_multiple_aggregator_quotes(self, url: str, base_params: dict) -> tuple:
        """Get quotes from multiple aggregators and return the best one."""
        print(f"\n[Multi-Aggregator] Testing {len(AGGREGATORS)} aggregators...")
        
        self._manage_rate_limit()
        
        best_result = None
        best_amount = 0
        best_price_impact = float('inf')
        aggregator_results = {}
        
        for i, (agg_name, agg_config) in enumerate(AGGREGATORS.items()):
            try:
                print(f"\n[{i+1}/{len(AGGREGATORS)}] Testing {agg_name} (cost: {agg_config['cost']} units)")
                
                # Prepare params with specific aggregator
                params = base_params.copy()
                params["aggregators"] = agg_name
                
                print(f"Request parameters for {agg_name}:")
                print(json.dumps(params, indent=2))
                
                # Make request
                print(f"Sending request to {agg_name}...")
                response = APIRetry.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                # Track computing units used
                self.computing_units_used += agg_config["cost"]
                print(f"[Rate Limit] Used {agg_config['cost']} units for {agg_name} (total: {self.computing_units_used}/100)")
                
                if 'data' in data and 'amountOut' in data['data']:
                    amount_out = int(data['data']['amountOut'])
                    price_impact = float(data['data'].get('priceImpact', 0))
                    
                    # Calculate rate for comparison
                    amount_decimal = Decimal(base_params['amountIn']) / Decimal(10**18)
                    weth_decimal = Decimal(amount_out) / Decimal(10**18)
                    rate = weth_decimal / amount_decimal if amount_decimal else Decimal('0')
                    
                    aggregator_results[agg_name] = {
                        "amount_out": amount_out,
                        "price_impact": price_impact,
                        "rate": float(rate),
                        "success": True
                    }
                    
                    print(f"✓ {agg_name} successful:")
                    print(f"  - WETH amount: {weth_decimal}")
                    print(f"  - Rate: {float(rate):.6f} WETH/token")
                    print(f"  - Price impact: {price_impact:.4f}%")
                    
                    # Check if this is the best result (highest WETH amount)
                    if amount_out > best_amount:
                        best_amount = amount_out
                        best_price_impact = price_impact
                        best_result = {
                            "amount": amount_out,
                            "price_impact": price_impact,
                            "aggregator": agg_name,
                            "rate": float(rate)
                        }
                    
                else:
                    print(f"✗ {agg_name} invalid response: {data}")
                    aggregator_results[agg_name] = {
                        "error": "Invalid response format",
                        "success": False
                    }
                
            except Exception as e:
                print(f"✗ {agg_name} failed: {str(e)}")
                aggregator_results[agg_name] = {
                    "error": str(e),
                    "success": False
                }
                
                # Still track computing units even on failure
                self.computing_units_used += agg_config["cost"]
            
            # Add delay between aggregator calls (except for the last one)
            if i < len(AGGREGATORS) - 1:
                delay = RATE_LIMIT_CONFIG["delay_between_aggregators"]
                print(f"[Rate Limit] Waiting {delay}s before next aggregator...")
                time.sleep(delay)
        
        # Update last quote time
        self.last_quote_time = time.time()
        
        # Display comparison results
        print(f"\n[Multi-Aggregator] Comparison Results:")
        print("-" * 60)
        successful_results = [(name, result) for name, result in aggregator_results.items() if result.get("success")]
        
        if successful_results:
            # Sort by WETH amount (best first)
            successful_results.sort(key=lambda x: x[1]["amount_out"], reverse=True)
            
            for i, (name, result) in enumerate(successful_results):
                symbol = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "  "
                amount_out = result["amount_out"]
                rate = result["rate"]
                price_impact = result["price_impact"]
                print(f"{symbol} {name}: {amount_out/1e18:.6f} WETH (rate: {rate:.6f}, impact: {price_impact:.4f}%)")
        
        failed_results = [(name, result) for name, result in aggregator_results.items() if not result.get("success")]
        if failed_results:
            print("\nFailed aggregators:")
            for name, result in failed_results:
                print(f"❌ {name}: {result.get('error', 'Unknown error')}")
        
        if best_result:
            print(f"\n🏆 Best result: {best_result['aggregator']} with {best_amount/1e18:.6f} WETH")
            return best_amount, best_price_impact, f"Direct ({best_result['aggregator']})", best_result
        else:
            raise Exception("All aggregators failed to provide quotes")
            
    def convert_pt_with_multi_aggregator(self, market_address: str, amount: int, receiver: str, slippage: float = 0.05) -> dict:
        """
        Convert PT tokens using multi-aggregator approach with fallback to original method.
        
        Args:
            market_address: The address of the Pendle market
            amount: Amount of PT tokens to convert (in wei)
            receiver: The address that will receive the tokens
            slippage: Maximum acceptable slippage (default: 0.05 = 5%)
            
        Returns:
            dict: Dictionary containing conversion details
        """
        print(f"\n=== PT Conversion with Multi-Aggregator ===")
        print(f"Market: {market_address}")
        print(f"Amount: {format_amount(str(amount))} PT")
        print(f"Receiver: {receiver}")
        
        # Load market data to get chain_id and token addresses
        market_mapping_path = Path(__file__).parent / "markets" / "market_mapping.json"
        
        with open(market_mapping_path, 'r') as f:
            mapping_data = json.load(f)
            
        market_address_lower = market_address.lower()
        markets_lower = {k.lower(): v for k, v in mapping_data["markets"].items()}
            
        if market_address_lower not in markets_lower:
            raise ValueError(f"Market {market_address} not found in market_mapping.json")
            
        market_data = markets_lower[market_address_lower]
        chain_id = int(market_data["chain_id"])
        pt_token = market_data["tokens"]["pt"].split("-")[1]
        
        # Get network info
        network = "ethereum" if chain_id == 1 else "base" if chain_id == 8453 else None
        if network is None:
            raise ValueError(f"Unsupported chain_id: {chain_id}")
            
        # Import COMMON_TOKENS for WETH address
        from config.networks import COMMON_TOKENS
        weth_address = COMMON_TOKENS[network]["WETH"]["address"]
        
        # Prepare API URL and parameters for multi-aggregator
        url = f"https://api-v2.pendle.finance/core/v1/sdk/{chain_id}/markets/{market_address}/swap"
        base_params = {
            "receiver": receiver,
            "slippage": slippage,
            "enableAggregator": "true",
            "amountIn": str(amount),
            "tokenIn": pt_token,
            "tokenOut": weth_address
        }
        
        # Try multi-aggregator approach first
        try:
            best_amount, best_price_impact, best_method, best_result = self._get_multiple_aggregator_quotes(url, base_params)
            
            # Create conversion details with multi-aggregator info
            conversion_details = {
                "source": f"Pendle SDK ({best_result['aggregator']})",
                "aggregator": best_result['aggregator'],
                "price_impact": f"{best_price_impact:.4f}",
                "rate": str(best_result['rate']),
                "fee_percentage": "0.0000%",
                "fallback": False,
                "note": f"Best result from {best_result['aggregator']} aggregator"
            }
            
            return {
                "best_amount": format_amount(str(best_amount)),
                "best_method": best_method,
                "conversion_details": conversion_details
            }
            
        except Exception as e:
            print(f"\n✗ All aggregators failed: {str(e)}")
            
            # Fallback to original method
            print("\n" + "="*80)
            print("FALLBACK MODE ACTIVATED")
            print("="*80)
            
            try:
                fallback_result = convert_pt(
                    market_address=market_address,
                    amount=amount,
                    receiver=receiver,
                    slippage=slippage
                )
                
                # Update conversion details to indicate fallback
                if fallback_result.get("best_amount"):
                    return {
                        "best_amount": fallback_result["best_amount"],
                        "best_method": "Fallback",
                        "conversion_details": {
                            "source": "Pendle SDK (Fallback)",
                            "aggregator": "fallback",
                            "price_impact": "0.0000",
                            "rate": "0",
                            "fee_percentage": "0.0000%",
                            "fallback": True,
                            "note": "Fallback to original method after multi-aggregator failure",
                            "fallback_reason": str(e)
                        }
                    }
                else:
                    raise Exception("Fallback method also failed")
                    
            except Exception as fallback_error:
                print(f"✗ Fallback also failed: {str(fallback_error)}")
                raise Exception(f"Both multi-aggregator and fallback failed. Multi-aggregator: {str(e)}, Fallback: {str(fallback_error)}")
        
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
                    pt_result = self.convert_pt_with_multi_aggregator(
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
                        conversion_details = pt_result.get("conversion_details", {
                            "source": "Pendle SDK",
                            "price_impact": "0.0000",
                            "rate": str(Decimal(weth_amount) / (position_data["pt"]["balance"] * Decimal('1e18'))),
                            "fee_percentage": "0.0000%",
                            "fallback": False,
                            "note": "Direct Conversion using Pendle SDK"
                        })
                    
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