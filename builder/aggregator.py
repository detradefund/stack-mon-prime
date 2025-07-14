import sys
from pathlib import Path
from typing import Dict, Any
import json
from decimal import Decimal
from web3 import Web3
from datetime import datetime, timezone
import time
import os

# Add parent directory and project root to PYTHONPATH
root_path = str(Path(__file__).parent.parent)
sys.path.append(root_path)
sys.path.append(str(Path(__file__).parent.parent))

from pendle.pendle_manager import PendleManager
from spot.balance_manager import SpotBalanceManager
from curve.balance.balance_manager import CurveBalanceManager
from convex.balance_manager import ConvexBalanceManager
from shares.supply_reader import SupplyReader
from config.networks import RPC_URLS
from aave.check_contracts import get_aave_balances
from vault.vault_reader import VaultReader
from euler.rpc_vault_client import EulerRPCClient

class BalanceAggregator:
    """
    Master aggregator that combines balances from multiple protocols.
    Currently supports:
    - Pendle (Ethereum + Base)
    - Spot (Ethereum + Base)
    - Curve (Base)
    - Convex (Ethereum)
    - Aave (Base)
    - Vault (Base)
    - Euler (Ethereum)
    """
    
    def __init__(self):
        self.pendle_manager = PendleManager(os.getenv('PRODUCTION_ADDRESS'))
        self.spot_manager = SpotBalanceManager()
        self.curve_manager = CurveBalanceManager("base", Web3(Web3.HTTPProvider(RPC_URLS["base"])))
        self.convex_manager = ConvexBalanceManager()
        self.vault_reader = VaultReader()
        self.euler_client = EulerRPCClient()
        
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
            "protocols": {},
            "spot": {}
        }
        
        # Get pendle balances
        try:
            print("\n" + "="*80)
            print("PENDLE BALANCE MANAGER")
            print("="*80 + "\n")
            pendle_balances = self.pendle_manager.run()
            if pendle_balances:
                result["protocols"]["pendle"] = pendle_balances
                print("✓ Pendle positions fetched successfully")
        except Exception as e:
            print(f"✗ Error fetching Pendle positions: {str(e)}")
            
        # Get Curve balances
        try:
            print("\n" + "="*80)
            print("CURVE BALANCE MANAGER")
            print("="*80 + "\n")
            print(f"Checking Curve positions for address: {checksum_address}")
            curve_data = self.curve_manager.get_pool_data("cbeth-f", checksum_address)
            if curve_data:
                result["protocols"]["curve"] = curve_data
                print("✓ Curve positions fetched successfully")
                
                # Add detailed logging
                if "base" in curve_data and "cbeth-f" in curve_data["base"]:
                    pool_data = curve_data["base"]["cbeth-f"]
                    
                    # Print withdrawable amounts
                    print("\nWithdrawable amounts:")
                    for symbol, data in pool_data["tokens"].items():
                        print(f"\n{symbol}:")
                        print(f"  Amount: {Decimal(data['amount']) / Decimal(10**data['decimals']):.6f}")
                        print(f"  Value in WETH: {Decimal(data['value']['WETH']['amount']) / Decimal(10**18):.6f}")
                        print(f"  Conversion rate: {data['value']['WETH']['conversion_details']['rate']}")
                        print(f"  Price impact: {data['value']['WETH']['conversion_details']['price_impact']}")
                        print(f"  Fee: {data['value']['WETH']['conversion_details']['fee_percentage']}")
                    
                    # Print rewards if any
                    if "rewards" in pool_data and pool_data["rewards"]:
                        print("\nRewards:")
                        for reward, reward_data in pool_data["rewards"].items():
                            print(f"\n{reward}:")
                            print(f"  Amount: {Decimal(reward_data['amount']) / Decimal(10**reward_data['decimals']):.6f}")
                            print(f"  Value in WETH: {Decimal(reward_data['value']['WETH']['amount']) / Decimal(10**18):.6f}")
                            print(f"  Conversion rate: {reward_data['value']['WETH']['conversion_details']['rate']}")
                            print(f"  Price impact: {reward_data['value']['WETH']['conversion_details']['price_impact']}")
                            print(f"  Fee: {reward_data['value']['WETH']['conversion_details']['fee_percentage']}")
                    
                    # Print totals
                    print("\nTotals:")
                    print(f"Total value in WETH: {Decimal(pool_data['totals']['wei']) / Decimal(10**18):.6f}")
                    print(f"Note: {pool_data['totals']['note']}")
        except Exception as e:
            print(f"✗ Error fetching Curve positions: {str(e)}")
        
        # Get Convex balances
        try:
            print("\n" + "="*80)
            print("CONVEX BALANCE MANAGER")
            print("="*80 + "\n")
            print(f"Checking Convex positions for address: {checksum_address}")
            convex_balances = self.convex_manager.get_balances(checksum_address)
            if convex_balances and convex_balances["convex"]["ethereum"]:
                result["protocols"]["convex"] = convex_balances["convex"]
                print("✓ Convex positions fetched successfully")
                
                # Add detailed logging for Convex
                if "ethereum" in convex_balances["convex"]:
                    for pool_name, pool_data in convex_balances["convex"]["ethereum"].items():
                        if pool_name == "totals":
                            continue
                        print(f"\nPool: {pool_name}")
                        
                        # Print LP tokens
                        if "value" in pool_data:
                            for token_symbol, token_data in pool_data["value"].items():
                                if "totals" in token_data:
                                    amount = Decimal(token_data["totals"]["wei"]) / Decimal(10**18)
                                    print(f"  {token_symbol}: {amount:.6f} WETH")
                        
                        # Print rewards
                        if "rewards" in pool_data and pool_data["rewards"]:
                            for reward_symbol, reward_data in pool_data["rewards"].items():
                                if "value" in reward_data and "WETH" in reward_data["value"]:
                                    amount = Decimal(reward_data["value"]["WETH"]["amount"]) / Decimal(10**18)
                                    print(f"  Rewards {reward_symbol}: {amount:.6f} WETH")
                        
                        # Print total
                        if "totals" in pool_data:
                            total = Decimal(pool_data["totals"]["wei"]) / Decimal(10**18)
                            print(f"  Total: {total:.6f} WETH")
            else:
                print("✓ No Convex positions found")
        except Exception as e:
            print(f"✗ Error fetching Convex positions: {str(e)}")
        
        # Get Aave balances
        try:
            print("\n" + "="*80)
            print("AAVE BALANCE MANAGER")
            print("="*80 + "\n")
            print(f"Checking Aave positions for address: {checksum_address}")
            aave_balances = get_aave_balances()
            if aave_balances and aave_balances.get("aave"):
                # Extract the data without the double "aave" key
                result["protocols"]["aave"] = {
                    "positions": aave_balances["aave"],
                    "net_position": aave_balances["net_position"]
                }
                print("✓ Aave positions fetched successfully")
                
                # Add detailed logging for Aave
                print("\nAave positions:")
                for position in aave_balances["aave"]:
                    print(f"\nContract: {position['contract']}")
                    print(f"  Symbol: {position['symbol']}")
                    print(f"  Balance: {Decimal(position['raw_balance']) / Decimal(10**position['decimals']):.6f}")
                    print(f"  Underlying: {position['underlying_symbol']}")
                    
                    if position.get("weth_conversion"):
                        weth_value = Decimal(position["weth_conversion"]["weth_value"]) / Decimal(10**18)
                        print(f"  Value in WETH: {weth_value:.6f}")
                        print(f"  Conversion rate: {position['weth_conversion']['conversion_rate']}")
                        print(f"  Source: {position['weth_conversion']['conversion_source']}")
                
                # Print net position
                if "net_position" in aave_balances:
                    net_pos = aave_balances["net_position"]
                    print(f"\nNet position:")
                    print(f"  Total supply: {Decimal(net_pos['total_supply_weth']) / Decimal(10**18):.6f} WETH")
                    print(f"  Total debt: {Decimal(net_pos['total_debt_weth']) / Decimal(10**18):.6f} WETH")
                    print(f"  Net position: {Decimal(net_pos['net_position_weth']) / Decimal(10**18):.6f} WETH")
            else:
                print("✓ No Aave positions found")
        except Exception as e:
            print(f"✗ Error fetching Aave positions: {str(e)}")
        
        # Get Vault balances
        try:
            print("\n" + "="*80)
            print("VAULT BALANCE MANAGER")
            print("="*80 + "\n")
            print(f"Checking Vault positions for address: {checksum_address}")
            vault_balances = self.vault_reader.get_vault_data()
            if vault_balances:
                result["protocols"]["vault"] = vault_balances
                print("✓ Vault positions fetched successfully")
                
                # Add detailed logging for Vault
                for protocol_name, protocol_data in vault_balances.items():
                    print(f"\nVault: {protocol_name}")
                    print(f"  Shares: {Decimal(protocol_data['shares']) / Decimal(10**18):.6f}")
                    print(f"  Share price: {Decimal(protocol_data['share_price']) / Decimal(10**6):.6f} USDC")
                    print(f"  USDC value: {Decimal(protocol_data['usdc_value']) / Decimal(10**6):.6f}")
                    
                    if protocol_data.get("weth_value"):
                        weth_value = Decimal(protocol_data["weth_value"]) / Decimal(10**18)
                        print(f"  WETH value: {weth_value:.6f}")
                        print(f"  Conversion rate: {protocol_data.get('conversion_rate', 'N/A')}")
                        print(f"  Source: {protocol_data.get('conversion_source', 'N/A')}")
            else:
                print("✓ No Vault positions found")
        except Exception as e:
            print(f"✗ Error fetching Vault positions: {str(e)}")
        
        # Get Euler balances
        try:
            print("\n" + "="*80)
            print("EULER BALANCE MANAGER")
            print("="*80 + "\n")
            print(f"Checking Euler positions for address: {checksum_address}")
            euler_balances = self.euler_client.get_balances(checksum_address)
            if euler_balances and euler_balances.get("euler") and euler_balances["euler"].get("ethereum"):
                result["protocols"]["euler"] = euler_balances["euler"]
                print("✓ Euler positions fetched successfully")
                
                # Add detailed logging for Euler
                euler_data = euler_balances["euler"]["ethereum"]
                if "net_position" in euler_data:
                    net_pos = euler_data["net_position"]
                    
                    # Print deposits
                    if net_pos.get("deposits"):
                        print("\nDeposits:")
                        for token_symbol, deposit_data in net_pos["deposits"].items():
                            if "value" in deposit_data and "WETH" in deposit_data["value"]:
                                amount = Decimal(deposit_data["value"]["WETH"]["amount"]) / Decimal(10**18)
                                print(f"  {token_symbol}: {amount:.6f} WETH")
                                print(f"    Conversion rate: {deposit_data['value']['WETH']['conversion_details']['rate']}")
                                print(f"    Source: {deposit_data['value']['WETH']['conversion_details']['source']}")
                    
                    # Print borrows
                    if net_pos.get("borrows"):
                        print("\nBorrows:")
                        for token_symbol, borrow_data in net_pos["borrows"].items():
                            if "value" in borrow_data and "WETH" in borrow_data["value"]:
                                amount = Decimal(borrow_data["value"]["WETH"]["amount"]) / Decimal(10**18)
                                print(f"  {token_symbol}: {amount:.6f} WETH")
                    
                    # Print net position
                    if "totals" in net_pos:
                        net_total = net_pos["totals"]["formatted"]
                        print(f"\nNet position: {net_total} ETH")
                    
                    # Print subaccounts
                    if net_pos.get("subaccounts"):
                        print("\nSubaccounts:")
                        for subaccount_addr, subaccount_data in net_pos["subaccounts"].items():
                            print(f"  {subaccount_addr}: {subaccount_data['net_eth']} ETH")
            else:
                print("✓ No Euler positions found")
        except Exception as e:
            print(f"✗ Error fetching Euler positions: {str(e)}")
        
        # Get spot balances
        try:
            print("\n" + "="*80)
            print("SPOT BALANCE MANAGER")
            print("="*80 + "\n")
            print("Processing method:")
            print("  - Querying native ETH balance")
            print("  - Querying balanceOf(address) for each token")
            print("  - Converting non-WETH tokens to WETH via CoWSwap")
            
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
                            "WETH": {
                                "amount": "0",
                                "decimals": 18,
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
                            "WETH": {
                                "amount": "0",
                                "decimals": 18,
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
                            "WETH": {
                                "amount": "0",
                                "decimals": 18,
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
                            "WETH": {
                                "amount": "0",
                                "decimals": 18,
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
        if protocol_name == "curve":
            # Handle Curve data structure
            if "base" in protocol_data:
                for pool_name, pool_data in protocol_data["base"].items():
                    if pool_name == "totals":
                        continue
                    # Add pool total (includes rewards)
                    if "totals" in pool_data:
                        key = f"{protocol_name}.base.{pool_name}"
                        value = f"{Decimal(pool_data['totals']['formatted']):.6f}"
                        positions[key] = value
                    # Add pool tokens (optional - for detailed breakdown)
                    if "value" in pool_data:
                        for token_symbol, token_info in pool_data["value"].items():
                            if "value" in token_info and "WETH" in token_info["value"]:
                                key = f"{protocol_name}.base.{pool_name}.{token_symbol}"
                                value = f"{Decimal(token_info['value']['WETH']['amount']) / Decimal(10**18):.6f}"
                                positions[key] = value
                    # Note: Rewards are now included in the pool total, not listed separately
        elif protocol_name == "convex":
            # Handle Convex data structure
            if "ethereum" in protocol_data:
                for pool_name, pool_data in protocol_data["ethereum"].items():
                    if pool_name == "totals":
                        continue
                    # Add pool total only (not individual components)
                    if "totals" in pool_data:
                        key = f"{protocol_name}.ethereum.{pool_name}"
                        value = f"{Decimal(pool_data['totals']['formatted']):.6f}"
                        positions[key] = value
        elif protocol_name == "aave":
            # Handle Aave data structure
            if "net_position" in protocol_data:
                net_pos = protocol_data["net_position"]
                net_value = Decimal(net_pos["net_position_weth"]) / Decimal(10**18)
                if net_value != 0:
                    key = f"{protocol_name}.base.net_position"
                    value = f"{net_value:.6f}"
                    positions[key] = value
        elif protocol_name == "vault":
            # Handle Vault data structure
            if isinstance(protocol_data, dict):
                for vault_name, vault_data in protocol_data.items():
                    if isinstance(vault_data, dict) and vault_data.get("weth_value"):
                        weth_value = Decimal(vault_data["weth_value"]) / Decimal(10**18)
                        key = f"{protocol_name}.base.{vault_name}"
                        value = f"{weth_value:.6f}"
                        positions[key] = value
        elif protocol_name == "euler":
            # Handle Euler data structure
            if "ethereum" in protocol_data:
                ethereum_data = protocol_data["ethereum"]
                if "net_position" in ethereum_data:
                    net_pos = ethereum_data["net_position"]
                    if "totals" in net_pos:
                        net_value = Decimal(net_pos["totals"]["wei"]) / Decimal(10**18)
                        if net_value != 0:
                            key = f"{protocol_name}.ethereum.net_position"
                            value = f"{net_value:.6f}"
                            positions[key] = value
        else:
            # Handle other protocols (Pendle)
            # Only process if protocol_data is not empty
            if protocol_data:
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
        # Initialize spot totals by network
        spot_totals = {}
        
        for network, network_data in all_balances["spot"].items():
            if network == "totals":
                continue
                
            network_total = Decimal('0')
            for token_name, token_data in network_data.items():
                if token_name != "totals" and isinstance(token_data, dict):
                    if "value" in token_data and "WETH" in token_data["value"]:
                        amount = Decimal(token_data["value"]["WETH"]["amount"]) / Decimal(10**18)
                        network_total += amount
            
            if network_total > 0:
                spot_totals[f"spot.{network}"] = f"{network_total:.6f}"
        
        # Add spot totals to positions
        positions.update(spot_totals)

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
    
    # Add retry logic for RPC calls
    max_retries = 3
    retry_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            all_balances = aggregator.get_all_balances(address)
            break
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Attempt {attempt + 1} failed: {str(e)}")
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print(f"All {max_retries} attempts failed")
                raise
    
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
