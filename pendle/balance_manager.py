import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import json
from web3 import Web3
from typing import Dict, Any, Tuple
from decimal import Decimal
import requests
import time
from datetime import datetime
from utils.retry import Web3Retry, APIRetry

"""
Pendle balance manager module.
Handles balance fetching and USDC valuation for Pendle Principal Tokens (PT).
Integrates with Pendle's API for accurate price discovery and fallback mechanisms.
"""

# Add parent directory to PYTHONPATH
root_path = str(Path(__file__).parent.parent)
sys.path.append(root_path)

# Load environment variables from parent directory
load_dotenv(Path(root_path) / '.env')

from config.networks import NETWORK_TOKENS, RPC_URLS, CHAIN_IDS
from cowswap.cow_client import get_quote

# Replace PT_ABI with minimal ABI
MINIMAL_PT_ABI = [
    {
        "constant": True,
        "inputs": [
            {
                "name": "_owner",
                "type": "address"
            }
        ],
        "name": "balanceOf",
        "outputs": [
            {
                "name": "balance",
                "type": "uint256"
            }
        ],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    }
]

class PendleBalanceManager:
    """
    Unified manager for Pendle positions handling:
    - Smart contract interactions
    - Balance fetching
    - Price discovery
    - WETH conversion
    """
    
    API_CONFIG = {
        "base_url": "https://api-v2.pendle.finance/core/v1/sdk",
        "default_slippage": "1",  # API parameter for quote requests
        "enable_aggregator": "true"
    }
    
    MAX_PRICE_IMPACT = 0.05  # 5%
    
    def __init__(self):
        # Initialize Web3 connections
        self.eth_w3 = Web3(Web3.HTTPProvider(RPC_URLS['ethereum']))
        self.base_w3 = Web3(Web3.HTTPProvider(RPC_URLS['base']))
        
        # Initialize contracts
        self.contracts = self._init_contracts()
        
        # Initialize current timestamp
        self.current_timestamp = int(datetime.now().timestamp())

    def _init_contracts(self) -> Dict:
        """Initialize Web3 contract instances for all Pendle PT tokens"""
        contracts = {}
        
        for network, tokens in NETWORK_TOKENS.items():
            contracts[network] = {}
            w3 = self.eth_w3 if network == 'ethereum' else self.base_w3
            
            for token_symbol, token_data in tokens.items():
                if token_data.get('protocol') == 'pendle':
                    contracts[network][token_symbol] = w3.eth.contract(
                        address=Web3.to_checksum_address(token_data['address']),
                        abi=MINIMAL_PT_ABI
                    )
        
        return contracts

    def is_pt_expired(self, token_data: Dict) -> bool:
        """
        Check if a PT token is expired
        
        Args:
            token_data: Token data from NETWORK_TOKENS
            
        Returns:
            bool: True if token is expired, False otherwise
        """
        expiry = token_data.get('expiry')
        if not expiry:
            return False
        return self.current_timestamp > expiry

    def _get_raw_balances(self, address: str) -> Dict:
        """Get raw balances from smart contracts"""
        try:
            checksum_address = Web3.to_checksum_address(address)
            balances = {}
            
            for network, network_contracts in self.contracts.items():
                if network_contracts:
                    balances[network] = {}
                    
                    for token_symbol, contract in network_contracts.items():
                        token_data = NETWORK_TOKENS[network][token_symbol]
                        balance = Web3Retry.call_contract_function(
                            contract.functions.balanceOf(checksum_address).call
                        )
                        
                        if balance > 0:
                            balances[network][token_symbol] = {
                                "amount": str(balance),
                                "decimals": token_data["decimals"]
                            }
            
            return balances
            
        except Exception as e:
            print(f"Error getting Pendle balances: {e}")
            return {}

    def _get_weth_quote(self, network: str, token_symbol: str, amount_in_wei: str) -> Tuple[int, float, Dict]:
        """
        Get WETH conversion quote from Pendle SDK API.
        
        Args:
            network: Network identifier (ethereum/base)
            token_symbol: PT token symbol
            amount_in_wei: Amount to convert in wei (18 decimals)
            
        Returns:
            Tuple containing:
            - WETH amount (18 decimals)
            - Price impact percentage
            - Conversion details
        """
        print(f"\nAttempting to get quote for {token_symbol}:")
        
        try:
            token_data = NETWORK_TOKENS[network][token_symbol]
            if self.is_pt_expired(token_data):
                print(f"\nToken {token_symbol} is expired (matured)")
                
                underlying_token = next(iter(token_data['underlying'].values()))
                print(f"Converting directly to underlying {underlying_token['symbol']} token (1:1)")
                
                print(f"\nConverting {underlying_token['symbol']} to WETH via CoWSwap:")
                result = get_quote(
                    network=network,
                    sell_token=underlying_token['address'],
                    buy_token=NETWORK_TOKENS[network]['WETH']['address'],
                    amount=amount_in_wei,
                    token_decimals=underlying_token['decimals'],
                    token_symbol=underlying_token['symbol']
                )
                
                if result["quote"]:
                    weth_amount = int(result["quote"]["quote"]["buyAmount"])
                    price_impact = float(result["conversion_details"].get("price_impact", "0"))
                    if isinstance(price_impact, str) and price_impact == "N/A":
                        price_impact = 0
                        
                    # Modify conversion details to reflect complete process
                    result["conversion_details"].update({
                        "source": "Matured PT",
                        "note": f"PT token matured - Direct 1:1 conversion to {underlying_token['symbol']}, then {result['conversion_details']['source']} quote for WETH"
                    })
                    
                    return weth_amount, price_impact/100, result["conversion_details"]
                
                raise Exception(f"Failed to convert {underlying_token['symbol']} to WETH")

            # If not expired, use Pendle API
            print(f"Requesting Pendle API quote...")
            
            url = f"{self.API_CONFIG['base_url']}/{CHAIN_IDS[network]}/markets/{token_data['market']}/swap"
            params = {
                "receiver": "0x0000000000000000000000000000000000000000",
                "slippage": self.API_CONFIG["default_slippage"],
                "enableAggregator": self.API_CONFIG["enable_aggregator"],
                "tokenIn": token_data["address"],
                "tokenOut": NETWORK_TOKENS[network]["WETH"]["address"],
                "amountIn": amount_in_wei
            }
            
            response = APIRetry.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if 'data' in data and 'amountOut' in data['data']:
                weth_amount = int(data['data']['amountOut'])
                price_impact = float(data['data'].get('priceImpact', 0))
                
                # Calculate rate for monitoring
                amount_decimal = Decimal(amount_in_wei) / Decimal(10**18)
                weth_decimal = Decimal(weth_amount) / Decimal(10**18)
                rate = weth_decimal / amount_decimal if amount_decimal else Decimal('0')
                
                print(f"✓ Quote successful:")
                print(f"  - Sell amount: {amount_decimal} {token_symbol}")
                print(f"  - Buy amount: {weth_decimal} WETH")
                print(f"  - Rate: {float(rate):.6f} WETH/{token_symbol}")
                print(f"  - Price impact: {price_impact:.4f}%")
                
                conversion_details = {
                    "source": "Pendle SDK",
                    "price_impact": f"{price_impact:.6f}",
                    "rate": f"{rate:.6f}",
                    "fee_percentage": "0.0000%",
                    "fallback": False,
                    "note": "Direct Conversion using Pendle SDK"
                }
                
                return weth_amount, price_impact, conversion_details
            
            print(f"✗ Invalid response from Pendle API: {data}")
            raise Exception("Invalid API response format")
                
        except Exception as e:
            print(f"✗ Technical error:")
            print(f"  {str(e)}")
            raise Exception(f"Failed to get Pendle quote: {str(e)}")

    def get_balances(self, address: str) -> Dict[str, Any]:
        """
        Get Pendle balances and convert to WETH
        """
        print("\n" + "="*80)
        print("PENDLE BALANCE MANAGER")
        print("="*80)
        
        try:
            # Get raw balances
            raw_balances = self._get_raw_balances(address)
            if not raw_balances:
                print("No Pendle positions found")
                return {"pendle": {}}
            
            # Process each network
            result = {"pendle": {}}
            total_weth_wei = 0
            
            for network, network_balances in raw_balances.items():
                print(f"\nProcessing network: {network}")
                network_total = 0
                
                for token_symbol, balance_data in network_balances.items():
                    print(f"\nProcessing token: {token_symbol}")
                    print(f"  Amount: {Decimal(balance_data['amount']) / Decimal(10**balance_data['decimals']):.6f} {token_symbol}")
                    
                    try:
                        # Get WETH quote
                        weth_amount, price_impact, conversion_details = self._get_weth_quote(
                            network=network,
                            token_symbol=token_symbol,
                            amount_in_wei=balance_data['amount']
                        )
                        
                        if weth_amount > 0:
                            network_total += weth_amount
                            total_weth_wei += weth_amount
                            
                            # Initialize network structure if not exists
                            if network not in result["pendle"]:
                                result["pendle"][network] = {}
                            
                            # Add token data
                            result["pendle"][network][token_symbol] = {
                                "amount": balance_data['amount'],
                                "decimals": balance_data['decimals'],
                                "value": {
                                    "WETH": {
                                        "amount": str(weth_amount),
                                        "decimals": 18,
                                        "conversion_details": conversion_details
                                    }
                                },
                                "totals": {
                                    "wei": weth_amount,
                                    "formatted": f"{weth_amount/1e18:.6f}"
                                }
                            }
                    except Exception as e:
                        print(f"Error processing {token_symbol}: {str(e)}")
                        continue
                
                # Add network totals if it has balances
                if network_total > 0:
                    result["pendle"][network]["totals"] = {
                        "wei": network_total,
                        "formatted": f"{network_total/1e18:.6f}"
                    }
            
            # Add protocol total
            if total_weth_wei > 0:
                result["pendle"]["totals"] = {
                    "wei": total_weth_wei,
                    "formatted": f"{total_weth_wei/1e18:.6f}"
                }
            
            print("\n[Pendle] Calculation complete")
            return result
            
        except Exception as e:
            print(f"Error getting Pendle balances: {str(e)}")
            return {"pendle": {}}

    def _get_failed_position(self, position: Dict) -> Dict:
        """Create position data structure for failed conversions"""
        return {
            "amount": position["amount"],
            "decimals": position["decimals"],
            "value": {
                "WETH": {
                    "amount": "0",
                    "decimals": 18,
                    "conversion_details": {
                        "source": "Failed",
                        "price_impact": "0",
                        "rate": "0",
                        "fallback": True
                    }
                }
            }
        }

def format_position_data(positions_data):
    result = {"pendle": {}}
    
    # Group by chain
    total_weth_wei = 0
    
    for network, positions in positions_data["pendle"].items():
        if network == "totals":
            continue  # Skip global totals during network processing
            
        formatted_positions = {}
        network_total = 0
        
        for position_name, position in positions.items():
            if position_name == "totals":
                continue  # Skip network totals during position processing
                
            try:
                weth_amount = int(position["totals"]["wei"])
                network_total += weth_amount
                
                formatted_positions[position_name] = {
                    "amount": position["amount"],
                    "decimals": position["decimals"],
                    "value": {
                        "WETH": {
                            "amount": str(weth_amount),
                            "decimals": 18,
                            "conversion_details": {
                                "source": position["value"]["WETH"]["conversion_details"]["source"],
                                "price_impact": position["value"]["WETH"]["conversion_details"]["price_impact"],
                                "rate": position["value"]["WETH"]["conversion_details"]["rate"],
                                "fee_percentage": position["value"]["WETH"]["conversion_details"].get("fee_percentage", "0.0000%"),
                                "fallback": position["value"]["WETH"]["conversion_details"]["fallback"],
                                "note": position["value"]["WETH"]["conversion_details"]["note"]
                            }
                        }
                    },
                    "totals": {
                        "wei": weth_amount,
                        "formatted": f"{weth_amount/1e18:.6f}"
                    }
                }
            except Exception as e:
                print(f"Warning: Could not process position {position_name}: {str(e)}")
                continue
        
        # Add network data with positions and network total
        if formatted_positions:  # Only add network if it has positions
            result["pendle"][network] = formatted_positions
            result["pendle"][network]["totals"] = {
                "wei": network_total,
                "formatted": f"{network_total/1e18:.6f}"
            }
            total_weth_wei += network_total
    
    # Add protocol total only if we have positions
    if total_weth_wei > 0:
        result["pendle"]["totals"] = {
            "wei": total_weth_wei,
            "formatted": f"{total_weth_wei/1e18:.6f}"
        }
    
    return result

def main():
    """
    CLI utility for testing Pendle balance aggregation.
    Uses production address by default.
    """
    # Production address
    PRODUCTION_ADDRESS = "0x66DbceE7feA3287B3356227d6F3DfF3CeFbC6F3C"
    
    # Use command line argument if provided, otherwise use production address
    test_address = sys.argv[1] if len(sys.argv) > 1 else PRODUCTION_ADDRESS
    
    manager = PendleBalanceManager()
    balances = manager.get_balances(test_address)
    formatted_balances = format_position_data(balances)
    
    print("\n" + "="*80)
    print("FINAL RESULT:")
    print("="*80 + "\n")
    print(json.dumps(formatted_balances, indent=2))

if __name__ == "__main__":
    main()