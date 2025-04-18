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
from .abis import PT_ABI

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
        "default_slippage": "1",
        "enable_aggregator": "true"
    }
    
    MAX_PRICE_IMPACT = 0.05  # 5%
    
    def __init__(self):
        # Initialize Web3 connections
        self.eth_w3 = Web3(Web3.HTTPProvider(RPC_URLS['ethereum']))
        self.base_w3 = Web3(Web3.HTTPProvider(RPC_URLS['base']))
        
        # Initialize contracts
        self.contracts = self._init_contracts()

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
                        abi=PT_ABI
                    )
        
        return contracts

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

    def _get_usdc_quote(self, network: str, token_symbol: str, amount_in_wei: str) -> Tuple[int, float]:
        """Get USDC conversion quote from Pendle API with retry mechanism"""
        retry_delays = [1, 3, 3]  # Délais en secondes entre les tentatives
        
        print(f"\nAttempting to get quote for {token_symbol}:")
        
        for attempt, delay in enumerate(retry_delays, 1):
            try:
                print(f"[Attempt {attempt}/3] Requesting Pendle API quote...")
                
                token_data = NETWORK_TOKENS[network][token_symbol]
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
                    
                    # Calculer le rate
                    amount_decimal = Decimal(amount_in_wei) / Decimal(10**18)
                    usdc_decimal = Decimal(usdc_amount) / Decimal(10**6)
                    rate = usdc_decimal / amount_decimal if amount_decimal else Decimal('0')
                    
                    print(f"✓ Quote successful:")
                    print(f"  - Sell amount: {amount_decimal} {token_symbol}")
                    print(f"  - Buy amount: {usdc_decimal} USDC")
                    print(f"  - Rate: {float(rate):.6f} USDC/{token_symbol}")
                    print(f"  - Price impact: {price_impact:.4f}%")
                    
                    return usdc_amount, price_impact
                
                print(f"✗ Invalid response from Pendle API: {data}")
                
            except Exception as e:
                print(f"✗ Technical error (attempt {attempt}/3):")
                print(f"  {str(e)}")
                
                if attempt < len(retry_delays):
                    print(f"  Retrying in {delay} seconds...")
                    time.sleep(delay)
                    continue
                
                print("✗ All retry attempts failed")
                raise Exception(f"Failed to get Pendle quote after 3 attempts: {str(e)}")

    def get_balances(self, address: str) -> Dict[str, Any]:
        """
        Retrieves all Pendle positions and their USDC valuations.
        """
        print("\n" + "="*80)
        print("PENDLE BALANCE MANAGER")
        print("="*80)
        
        print("\nDebug get_balances:")
        print(f"Processing address: {address}")
        checksum_address = Web3.to_checksum_address(address)
        print(f"Checksum address: {checksum_address}")
        
        result = {"pendle": {}}
        total_usdc_wei = 0  # Ajout du compteur pour le total
        
        # Process each supported network
        for network in ["ethereum", "base"]:
            print(f"\nProcessing network: {network}")
            network_tokens = NETWORK_TOKENS[network]
            network_result = {}
            
            # Find and process all Pendle PT tokens
            for token_symbol, token_data in network_tokens.items():
                if token_data.get("protocol") != "pendle":
                    continue
                    
                print(f"\nProcessing token: {token_symbol}")
                
                # Get token balance using checksum address
                all_balances = self._get_raw_balances(checksum_address)
                balance = int(all_balances[network][token_symbol]['amount']) if network in all_balances and token_symbol in all_balances[network] else 0
                
                if balance == 0:
                    print(f"No balance found for {token_symbol}")
                    continue
                
                # Afficher les informations de balance après l'avoir calculée
                decimals = token_data["decimals"]
                print(f"Amount: {balance} (decimals: {decimals})")
                print(f"Formatted amount: {(Decimal(balance) / Decimal(10**decimals)):.6f} {token_symbol}")
                
                # Get USDC valuation
                try:
                    usdc_amount, price_impact = self._get_usdc_quote(
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
                    source = "Pendle API"
                    
                except Exception as e:
                    print(f"✗ Valuation failed: {str(e)}")
                    usdc_amount = 0
                    price_impact = 0
                    rate = Decimal('0')
                    fallback = True
                    source = "Failed"
                
                # Add position to results
                network_result[token_symbol] = {
                    "amount": str(balance),
                    "decimals": token_data["decimals"],
                    "value": {
                        "USDC": {
                            "amount": str(usdc_amount),
                            "decimals": 6,
                            "conversion_details": {
                                "source": source,
                                "price_impact": f"{price_impact:.6f}",
                                "rate": f"{rate:.6f}",
                                "fallback": fallback
                            }
                        }
                    }
                }
                
                # Mise à jour du total USDC
                if "value" in network_result[token_symbol] and "USDC" in network_result[token_symbol]["value"]:
                    total_usdc_wei += int(network_result[token_symbol]["value"]["USDC"]["amount"])
            
            result["pendle"][network] = network_result
        
        # À la fin de la méthode, avant le return:
        print("\n" + "="*80)
        print(f"TOTAL PENDLE VALUE: {total_usdc_wei / 1_000_000:.2f} USDC")
        print("="*80)
        
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
    global_total = 0
    
    # Group by chain
    for chain, positions in positions_data["pendle"].items():
        chain_total = 0
        formatted_positions = {}
        
        for position_name, position in positions.items():
            try:
                # Calculate USDC value
                usdc_value = int(position["value"]["USDC"]["amount"])
                chain_total += usdc_value
                global_total += usdc_value
                
                # Format position with standardized structure
                formatted_positions[position_name] = {
                    "amount": position["amount"],
                    "decimals": position["decimals"],
                    "value": {
                        "USDC": {
                            "amount": position["value"]["USDC"]["amount"],
                            "decimals": position["value"]["USDC"]["decimals"],
                            "conversion_details": {
                                "source": position["value"]["USDC"]["conversion_details"]["source"],
                                "price_impact": f"{float(position['value']['USDC']['conversion_details']['price_impact'])*100:.4f}%",
                                "rate": position["value"]["USDC"]["conversion_details"]["rate"],
                                "fee_percentage": "0.0000%",
                                "fallback": position["value"]["USDC"]["conversion_details"]["fallback"],
                                "note": "Via Pendle API price oracle"
                            }
                        }
                    }
                }
            except Exception as e:
                print(f"Warning: Could not process position {position_name}: {str(e)}")
                continue
        
        # Add chain data with positions and chain total
        result["pendle"][chain] = {
            **formatted_positions,
            "usdc_totals": {
                "total": {
                    "wei": chain_total,
                    "formatted": f"{chain_total/1e6:.6f}"
                }
            }
        }
    
    # Add global total for all chains
    result["pendle"]["usdc_totals"] = {
        "total": {
            "wei": global_total,
            "formatted": f"{global_total/1e6:.6f}"
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