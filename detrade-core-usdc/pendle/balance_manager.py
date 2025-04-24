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
    - USDC conversion
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
                        balance = contract.functions.balanceOf(checksum_address).call()
                        
                        if balance > 0:
                            balances[network][token_symbol] = {
                                "amount": str(balance),
                                "decimals": token_data["decimals"]
                            }
            
            return balances
            
        except Exception as e:
            print(f"Error getting Pendle balances: {e}")
            return {}

    def _get_usdc_quote(self, network: str, token_symbol: str, amount_in_wei: str) -> Tuple[int, float, Dict]:
        """
        Get USDC conversion quote from Pendle SDK API.
        
        Args:
            network: Network identifier (ethereum/base)
            token_symbol: PT token symbol
            amount_in_wei: Amount to convert in wei (18 decimals)
            
        Returns:
            Tuple containing:
            - USDC amount (6 decimals)
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
                
                print(f"\nConverting {underlying_token['symbol']} to USDC via CoWSwap:")
                result = get_quote(
                    network=network,
                    sell_token=underlying_token['address'],
                    buy_token=NETWORK_TOKENS[network]['USDC']['address'],
                    amount=amount_in_wei,
                    token_decimals=underlying_token['decimals'],
                    token_symbol=underlying_token['symbol']
                )
                
                if result["quote"]:
                    usdc_amount = int(result["quote"]["quote"]["buyAmount"])
                    price_impact = float(result["conversion_details"].get("price_impact", "0"))
                    if isinstance(price_impact, str) and price_impact == "N/A":
                        price_impact = 0
                        
                    # Modify conversion details to reflect complete process
                    result["conversion_details"].update({
                        "source": "Matured PT",
                        "note": f"PT token matured - Direct 1:1 conversion to {underlying_token['symbol']}, then {result['conversion_details']['source']} quote for USDC"
                    })
                    
                    return usdc_amount, price_impact/100, result["conversion_details"]
                
                raise Exception(f"Failed to convert {underlying_token['symbol']} to USDC")

            # If not expired, use Pendle API
            print(f"Requesting Pendle API quote...")
            
            url = f"{self.API_CONFIG['base_url']}/{CHAIN_IDS[network]}/markets/{token_data['market']}/swap"
            params = {
                "receiver": "0x0000000000000000000000000000000000000000",
                "slippage": self.API_CONFIG["default_slippage"],
                "enableAggregator": self.API_CONFIG["enable_aggregator"],
                "tokenIn": token_data["address"],
                "tokenOut": NETWORK_TOKENS[network]["USDC"]["address"],
                "amountIn": amount_in_wei
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if 'data' in data and 'amountOut' in data['data']:
                usdc_amount = int(data['data']['amountOut'])
                price_impact = float(data['data'].get('priceImpact', 0))
                
                # Calculate rate for monitoring
                amount_decimal = Decimal(amount_in_wei) / Decimal(10**18)
                usdc_decimal = Decimal(usdc_amount) / Decimal(10**6)
                rate = usdc_decimal / amount_decimal if amount_decimal else Decimal('0')
                
                print(f"✓ Quote successful:")
                print(f"  - Sell amount: {amount_decimal} {token_symbol}")
                print(f"  - Buy amount: {usdc_decimal} USDC")
                print(f"  - Rate: {float(rate):.6f} USDC/{token_symbol}")
                print(f"  - Price impact: {price_impact:.4f}%")
                
                conversion_details = {
                    "source": "Pendle SDK",
                    "price_impact": f"{price_impact:.6f}",
                    "rate": f"{rate:.6f}",
                    "fee_percentage": "0.0000%",
                    "fallback": False,
                    "note": "Direct Conversion using Pendle SDK"
                }
                
                return usdc_amount, price_impact, conversion_details
            
            print(f"✗ Invalid response from Pendle API: {data}")
            raise Exception("Invalid API response format")
                
        except Exception as e:
            print(f"✗ Technical error:")
            print(f"  {str(e)}")
            raise Exception(f"Failed to get Pendle quote: {str(e)}")

    def get_balances(self, address: str) -> Dict[str, Any]:
        print("\n" + "="*80)
        print("PENDLE BALANCE MANAGER")
        print("="*80)
        
        checksum_address = Web3.to_checksum_address(address)
        
        # Fetch all balances first
        all_balances = self._get_raw_balances(checksum_address)
        
        result = {"pendle": {}}
        total_usdc_wei = 0
        
        # Process each supported network
        for network in ["ethereum", "base"]:
            print(f"\nProcessing network: {network}")
            network_tokens = NETWORK_TOKENS[network]
            network_result = {}
            network_total = 0
            
            # Process each Pendle position
            for token_symbol, token_data in network_tokens.items():
                if token_data.get("protocol") != "pendle":
                    continue
                
                balance = int(all_balances[network][token_symbol]['amount']) if network in all_balances and token_symbol in all_balances[network] else 0
                
                if balance == 0:
                    continue
                
                print(f"\nProcessing position: {token_symbol}")
                
                # Contract information
                print(f"\nContract information:")
                print(f"  token: {token_data['address']} ({token_symbol})")
                print(f"  market: {token_data['market']}")
                if token_data.get('expiry'):
                    print(f"  expiry: {token_data['expiry']}")
                print(f"  underlying: {next(iter(token_data['underlying'].values()))['symbol']}")
                
                # Balance information
                print("\nQuerying balance:")
                print(f"  Function: balanceOf({checksum_address})")
                print(f"  Amount: {balance} (decimals: {token_data['decimals']})")
                print(f"  Formatted: {(Decimal(balance) / Decimal(10**token_data['decimals'])):.6f} {token_symbol}")
                
                # Get USDC valuation
                try:
                    usdc_amount, price_impact, conversion_details = self._get_usdc_quote(
                        network=network,
                        token_symbol=token_symbol,
                        amount_in_wei=str(balance)
                    )
                    usdc_normalized = Decimal(usdc_amount) / Decimal(10**6)
                    
                    # Calculer le rate
                    rate = Decimal(usdc_amount) / Decimal(balance) * Decimal(10 ** (18 - 6)) if balance > 0 else Decimal('0')
                    
                    print(f"✓ Valuation successful:")
                    print(f"  - USDC value: {usdc_normalized}")
                    print(f"  - Rate: {float(rate):.6f}")
                    print(f"  - Price impact: {price_impact:.4f}%")
                    
                    fallback = False
                    source = "Pendle SDK"
                    note = "Direct Conversion using Pendle SDK"
                
                except Exception as e:
                    print(f"✗ Valuation failed: {str(e)}")
                    usdc_amount = 0
                    price_impact = 0
                    rate = Decimal('0')
                    fallback = True
                    source = "Failed"
                    note = "Failed to get Pendle SDK quote"
                
                # Add position to results
                if usdc_amount > 0:
                    network_total += usdc_amount
                    network_result[token_symbol] = {
                        "amount": str(balance),
                        "decimals": token_data["decimals"],
                        "value": {
                            "USDC": {
                                "amount": str(usdc_amount),
                                "decimals": 6,
                                "conversion_details": conversion_details
                            }
                        }
                    }
            
            if network_result:
                result["pendle"][network] = network_result
                # Add network-level USDC totals
                result["pendle"][network]["usdc_totals"] = {
                    "total": {
                        "wei": network_total,
                        "formatted": f"{network_total/1e6:.6f}"
                    }
                }
                total_usdc_wei += network_total
        
        # Add protocol-level USDC totals
        result["pendle"]["usdc_totals"] = {
            "total": {
                "wei": total_usdc_wei,
                "formatted": f"{total_usdc_wei/1e6:.6f}"
            }
        }
        
        # Display detailed summary
        print("\n[Pendle] Calculation complete")
        
        # Display detailed positions
        for network in result["pendle"]:
            if network != "usdc_totals":
                for token, data in result["pendle"][network].items():
                    if token != "usdc_totals" and isinstance(data, dict) and "value" in data:
                        amount = int(data["value"]["USDC"]["amount"])
                        if amount > 0:
                            formatted_amount = amount / 10**6
                            print(f"pendle.{network}.{token}: {formatted_amount:.6f} USDC")
        
        return result

    def _get_failed_position(self, position: Dict) -> Dict:
        """Create position data structure for failed conversions"""
        return {
            "amount": position["amount"],
            "decimals": position["decimals"],
            "value": {
                "USDC": {
                    "amount": "0",
                    "decimals": 6,
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
    total_usdc_wei = 0
    
    for network, positions in positions_data["pendle"].items():
        if network == "usdc_totals":
            continue  # Skip global totals during network processing
            
        formatted_positions = {}
        network_total = 0
        
        for position_name, position in positions.items():
            if position_name == "usdc_totals":
                continue  # Skip network totals during position processing
                
            try:
                usdc_amount = int(position["value"]["USDC"]["amount"])
                network_total += usdc_amount
                
                formatted_positions[position_name] = {
                    "amount": position["amount"],
                    "decimals": position["decimals"],
                    "value": {
                        "USDC": {
                            "amount": str(usdc_amount),
                            "decimals": 6,
                            "conversion_details": {
                                "source": position["value"]["USDC"]["conversion_details"]["source"],
                                "price_impact": position["value"]["USDC"]["conversion_details"]["price_impact"],
                                "rate": position["value"]["USDC"]["conversion_details"]["rate"],
                                "fee_percentage": position["value"]["USDC"]["conversion_details"].get("fee_percentage", "0.0000%"),
                                "fallback": position["value"]["USDC"]["conversion_details"]["fallback"],
                                "note": position["value"]["USDC"]["conversion_details"]["note"]
                            }
                        }
                    }
                }
            except Exception as e:
                print(f"Warning: Could not process position {position_name}: {str(e)}")
                continue
        
        # Add network data with positions and network total
        if formatted_positions:  # Only add network if it has positions
            result["pendle"][network] = formatted_positions
            result["pendle"][network]["usdc_totals"] = {
                "total": {
                    "wei": network_total,
                    "formatted": f"{network_total/10**6:.6f}"
                }
            }
            total_usdc_wei += network_total
    
    # Add protocol total only if we have positions
    if total_usdc_wei > 0:
        result["pendle"]["usdc_totals"] = {
            "total": {
                "wei": total_usdc_wei,
                "formatted": f"{total_usdc_wei/10**6:.6f}"
            }
        }
    
    return result

def main():
    """
    CLI utility for testing Pendle balance aggregation.
    Accepts address as argument or uses DEFAULT_USER_ADDRESS from environment.
    """
    test_address = sys.argv[1] if len(sys.argv) > 1 else os.getenv('DEFAULT_USER_ADDRESS')
    
    if not test_address:
        print("Error: No address provided and DEFAULT_USER_ADDRESS not found in .env")
        sys.exit(1)
        
    manager = PendleBalanceManager()
    balances = manager.get_balances(test_address)
    formatted_balances = format_position_data(balances)
    
    print("\n" + "="*80)
    print("FINAL RESULT:")
    print("="*80 + "\n")
    print(json.dumps(formatted_balances, indent=2))

if __name__ == "__main__":
    main()