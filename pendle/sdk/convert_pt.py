"""
Module for handling Pendle PT conversion operations.
"""
from dataclasses import dataclass
from typing import Optional
import requests
import json
from decimal import Decimal
from pathlib import Path
import sys
from web3 import Web3

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent.parent))
from config.networks import COMMON_TOKENS, RPC_URLS
from cowswap.cow_client import get_quote

def format_amount(wei_str):
    eth = int(wei_str) / 1e18
    return f"{eth:,.6f}"

@dataclass
class ConvertPTQuote:
    """Class to handle PT conversion quotes from Pendle."""
    
    def __init__(
        self,
        market_address: str,
        amount_in: int,
        production_address: str,
        use_aggregator: bool = True,
        slippage: float = 0.05,  # 5% default slippage
    ):
        """
        Initialize the ConvertPTQuote.
        
        Args:
            market_address: The address of the Pendle market
            amount_in: Amount of PT tokens to convert (in wei)
            production_address: The address that will receive the tokens
            use_aggregator: Whether to use Pendle's aggregator (default: True)
            slippage: Maximum acceptable slippage (default: 0.05 = 5%)
        """
        self.market_address = market_address
        self.amount_in = amount_in
        self.receiver = production_address
        self.use_aggregator = use_aggregator
        self.slippage = slippage
        
        # Load market data
        market_data = self._load_market_data()
        
        # Get token addresses and chain_id from market data
        self.pt_token = market_data["tokens"]["pt"].split("-")[1]  # Remove chain_id prefix
        self.sy_token = market_data["tokens"]["sy"].split("-")[1]
        self.underlying_token = market_data["tokens"]["underlyingAsset"].split("-")[1]
        self.chain_id = int(market_data["chain_id"])
        self.market_name = market_data["name"]
        
    def _load_market_data(self) -> dict:
        """Load market data from market_mapping.json"""
        market_mapping_path = Path(__file__).parent.parent / "markets" / "market_mapping.json"
        
        with open(market_mapping_path, 'r') as f:
            data = json.load(f)
            
        # Convert market address to lowercase for case-insensitive comparison
        market_address_lower = self.market_address.lower()
        markets_lower = {k.lower(): v for k, v in data["markets"].items()}
            
        if market_address_lower not in markets_lower:
            raise ValueError(f"Market {self.market_address} not found in market_mapping.json")
            
        return markets_lower[market_address_lower]
        
    def get_quote(self) -> dict:
        """
        Get a quote for converting PT tokens.
        
        Returns:
            dict: The quote response containing amountOut, priceImpact, and transaction data
        """
        if self.use_aggregator:
            # Use aggregator to convert directly to WETH
            base_url = f"https://api-v2.pendle.finance/core/v1/sdk/{self.chain_id}/markets/{self.market_address}/swap"
            network = "ethereum" if self.chain_id == 1 else "base" if self.chain_id == 8453 else None
            if network is None:
                raise ValueError(f"Unsupported chain_id: {self.chain_id}")
                
            weth_address = COMMON_TOKENS[network]["WETH"]["address"]
            params = {
                "receiver": self.receiver,
                "slippage": self.slippage,
                "enableAggregator": "true",
                "amountIn": str(self.amount_in),
                "tokenIn": self.pt_token,
                "tokenOut": weth_address  # Specify WETH as output token
            }
        else:
            # Convert to SY first
            base_url = f"https://api-v2.pendle.finance/core/v1/sdk/{self.chain_id}/markets/{self.market_address}/swap"
            params = {
                "receiver": self.receiver,
                "slippage": self.slippage,
                "enableAggregator": "false",
                "amountIn": str(self.amount_in),
                "tokenIn": self.pt_token,
                "tokenOut": self.sy_token
            }
        
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        
        return response.json()
    
    def get_amount_out(self) -> int:
        """
        Get the expected amount out from the conversion.
        
        Returns:
            int: The expected amount out in wei
        """
        quote = self.get_quote()
        return int(quote["data"]["amountOut"])
    
    def get_price_impact(self) -> float:
        """
        Get the price impact of the conversion.
        
        Returns:
            float: The price impact as a decimal
        """
        quote = self.get_quote()
        return float(quote["data"]["priceImpact"])
    
    def get_transaction_data(self) -> dict:
        """
        Get the transaction data for executing the conversion.
        
        Returns:
            dict: The transaction data including contract call parameters
        """
        quote = self.get_quote()
        return {
            "tx": quote["tx"],
            "tokenApprovals": quote["tokenApprovals"]
        }

def convert_pt(market_address: str, amount: int, receiver: str = None, slippage: float = 0.05) -> dict:
    """
    Convert PT tokens to underlying asset.
    Tries both methods (with and without aggregator) and returns the best result.
    
    Args:
        market_address: The address of the Pendle market
        amount: Amount of PT tokens to convert (in wei)
        receiver: The address that will receive the tokens (optional)
        slippage: Maximum acceptable slippage (default: 0.05 = 5%)
        
    Returns:
        dict: Dictionary containing conversion summary with both methods and the best result
    """
    print(f"\n=== Starting PT Conversion Process ===")
    print(f"Market Address: {market_address}")
    print(f"Amount: {format_amount(str(amount))} PT")
    print(f"Receiver: {receiver}")
    print(f"Slippage: {slippage * 100}%")
    
    if receiver is None:
        raise ValueError("receiver address is required")
    
    # Get market data and token info (common for both methods)
    print("\nLoading market data...")
    quote = ConvertPTQuote(
        market_address=market_address,
        amount_in=amount,
        production_address=receiver,
        use_aggregator=True,  # Doesn't matter which one we use for market data
        slippage=slippage
    )
    
    # Get market data
    market_data = quote._load_market_data()
    market_name = market_data["name"]
    pt_token = market_data["tokens"]["pt"].split("-")[1]
    sy_token = market_data["tokens"]["sy"].split("-")[1]
    underlying_token = market_data["tokens"]["underlyingAsset"].split("-")[1]
    chain_id = market_data["chain_id"]
    
    print(f"Market Name: {market_name}")
    print(f"Chain ID: {chain_id}")
    print(f"PT Token: {pt_token}")
    print(f"SY Token: {sy_token}")
    print(f"Underlying Token: {underlying_token}")
    
    # Get Web3 instance
    network = "ethereum" if chain_id == "1" else "base" if chain_id == "8453" else None
    if network is None:
        raise ValueError(f"Unsupported chain_id: {chain_id}")
    w3 = Web3(Web3.HTTPProvider(RPC_URLS[network]))
    print(f"Network: {network}")
    
    # Get token info
    print("\nFetching token information...")
    pt_contract = w3.eth.contract(address=w3.to_checksum_address(pt_token), abi=[
        {"inputs": [], "name": "symbol", "outputs": [{"internalType": "string", "name": "", "type": "string"}], "stateMutability": "view", "type": "function"},
        {"inputs": [], "name": "name", "outputs": [{"internalType": "string", "name": "", "type": "string"}], "stateMutability": "view", "type": "function"}
    ])
    pt_symbol = pt_contract.functions.symbol().call()
    pt_name = pt_contract.functions.name().call()
    print(f"PT Token Info: {pt_symbol} ({pt_name})")
    
    sy_contract = w3.eth.contract(address=w3.to_checksum_address(sy_token), abi=[
        {"inputs": [], "name": "symbol", "outputs": [{"internalType": "string", "name": "", "type": "string"}], "stateMutability": "view", "type": "function"},
        {"inputs": [], "name": "name", "outputs": [{"internalType": "string", "name": "", "type": "string"}], "stateMutability": "view", "type": "function"}
    ])
    sy_symbol = sy_contract.functions.symbol().call()
    sy_name = sy_contract.functions.name().call()
    print(f"SY Token Info: {sy_symbol} ({sy_name})")
    
    underlying_contract = w3.eth.contract(address=w3.to_checksum_address(underlying_token), abi=[
        {"inputs": [], "name": "symbol", "outputs": [{"internalType": "string", "name": "", "type": "string"}], "stateMutability": "view", "type": "function"},
        {"inputs": [], "name": "name", "outputs": [{"internalType": "string", "name": "", "type": "string"}], "stateMutability": "view", "type": "function"}
    ])
    underlying_symbol = underlying_contract.functions.symbol().call()
    underlying_name = underlying_contract.functions.name().call()
    print(f"Underlying Token Info: {underlying_symbol} ({underlying_name})")
    
    # Try both methods
    results = {}
    
    # Method 1: With aggregator
    print("\n=== Trying Method 1: With Aggregator ===")
    try:
        print("Getting quote with aggregator...")
        quote_with_aggregator = ConvertPTQuote(
            market_address=market_address,
            amount_in=amount,
            production_address=receiver,
            use_aggregator=True,
            slippage=slippage
        )
        output_amt_with_aggregator = quote_with_aggregator.get_amount_out()
        price_impact_with_aggregator = quote_with_aggregator.get_price_impact()
        
        print(f"Success! Output amount: {format_amount(str(output_amt_with_aggregator))} WETH")
        print(f"Price impact: {price_impact_with_aggregator * 100:.4f}%")
        
        results["with_aggregator"] = {
            "amount_out": output_amt_with_aggregator,
            "price_impact": price_impact_with_aggregator,
            "steps": [{
                "step": 1,
                "from": {
                    "amount": format_amount(str(amount)),
                    "token": pt_symbol,
                    "name": pt_name
                },
                "to": {
                    "amount": format_amount(str(output_amt_with_aggregator)),
                    "token": "WETH",
                    "name": "Wrapped Ether"
                },
                "method": "Pendle Aggregator",
                "price_impact": f"{price_impact_with_aggregator * 100:.4f}%"
            }]
        }
    except Exception as e:
        error_msg = str(e)
        print(f"✗ Failed with aggregator: {error_msg}")
        
        # Check if it's a MarketProportionTooHigh error and retry with doubled slippage
        if "MarketProportionTooHigh" in error_msg or "Market liquidity is likely insufficient" in error_msg:
            print(f"⚠️  Detected liquidity issue. Retrying with doubled slippage ({slippage * 2 * 100:.1f}%)...")
            try:
                quote_with_aggregator_retry = ConvertPTQuote(
                    market_address=market_address,
                    amount_in=amount,
                    production_address=receiver,
                    use_aggregator=True,
                    slippage=slippage * 2  # Double the slippage
                )
                output_amt_with_aggregator_retry = quote_with_aggregator_retry.get_amount_out()
                price_impact_with_aggregator_retry = quote_with_aggregator_retry.get_price_impact()
                
                print(f"✓ Retry successful! Output amount: {format_amount(str(output_amt_with_aggregator_retry))} WETH")
                print(f"Price impact: {price_impact_with_aggregator_retry * 100:.4f}%")
                
                results["with_aggregator"] = {
                    "amount_out": output_amt_with_aggregator_retry,
                    "price_impact": price_impact_with_aggregator_retry,
                    "steps": [{
                        "step": 1,
                        "from": {
                            "amount": format_amount(str(amount)),
                            "token": pt_symbol,
                            "name": pt_name
                        },
                        "to": {
                            "amount": format_amount(str(output_amt_with_aggregator_retry)),
                            "token": "WETH",
                            "name": "Wrapped Ether"
                        },
                        "method": "Pendle Aggregator (Retry with 2x slippage)",
                        "price_impact": f"{price_impact_with_aggregator_retry * 100:.4f}%"
                    }]
                }
            except Exception as retry_e:
                print(f"✗ Retry also failed: {str(retry_e)}")
                results["with_aggregator"] = {
                    "error": f"Original: {error_msg} | Retry: {str(retry_e)}",
                    "steps": []
                }
        else:
            results["with_aggregator"] = {
                "error": error_msg,
                "steps": []
            }
    
    # Method 2: Without aggregator
    print("\n=== Trying Method 2: Without Aggregator ===")
    try:
        print("Getting quote without aggregator...")
        quote_without_aggregator = ConvertPTQuote(
            market_address=market_address,
            amount_in=amount,
            production_address=receiver,
            use_aggregator=False,
            slippage=slippage
        )
        output_amt_without_aggregator = quote_without_aggregator.get_amount_out()
        price_impact_without_aggregator = quote_without_aggregator.get_price_impact()
        
        print(f"Success! Output amount: {format_amount(str(output_amt_without_aggregator))} {underlying_symbol}")
        print(f"Price impact: {price_impact_without_aggregator * 100:.4f}%")
        
        # Get CowSwap quote for converting underlying to WETH
        print("\nGetting CowSwap quote for final conversion...")
        cowswap_result = get_quote(
            network=network,
            sell_token=underlying_token,
            buy_token=COMMON_TOKENS[network]["WETH"]["address"],
            amount=str(output_amt_without_aggregator),
            token_decimals=18,
            token_symbol=underlying_symbol
        )
        
        steps = [
            {
                "step": 1,
                "from": {
                    "amount": format_amount(str(amount)),
                    "token": pt_symbol,
                    "name": pt_name
                },
                "to": {
                    "amount": format_amount(str(output_amt_without_aggregator)),
                    "token": sy_symbol,
                    "name": sy_name
                },
                "method": "Direct Pendle API",
                "price_impact": f"{price_impact_without_aggregator * 100:.4f}%"
            },
            {
                "step": 2,
                "from": {
                    "amount": format_amount(str(output_amt_without_aggregator)),
                    "token": sy_symbol,
                    "name": sy_name
                },
                "to": {
                    "amount": format_amount(str(output_amt_without_aggregator)),
                    "token": underlying_symbol,
                    "name": underlying_name
                },
                "method": "1:1 conversion"
            }
        ]
        
        # Add CowSwap step if quote is successful
        if cowswap_result["quote"]:
            weth_amount = int(cowswap_result["quote"]["quote"]["buyAmount"])
            cowswap_price_impact = float(cowswap_result["conversion_details"].get("price_impact", "0"))
            if isinstance(cowswap_price_impact, str) and cowswap_price_impact == "N/A":
                cowswap_price_impact = 0
                
            print(f"CowSwap quote successful! Output amount: {format_amount(str(weth_amount))} WETH")
            print(f"CowSwap price impact: {cowswap_price_impact:.4f}%")
                
            steps.append({
                "step": 3,
                "from": {
                    "amount": format_amount(str(output_amt_without_aggregator)),
                    "token": underlying_symbol,
                    "name": underlying_name
                },
                "to": {
                    "amount": format_amount(str(weth_amount)),
                    "token": "WETH",
                    "name": "Wrapped Ether"
                },
                "method": "CowSwap",
                "price_impact": f"{cowswap_price_impact:.4f}%",
                "status": "success"
            })
            # Update final amount to WETH amount
            output_amt_without_aggregator = weth_amount
        else:
            print(f"✗ CowSwap quote failed: {cowswap_result['conversion_details']['note']}")
            steps.append({
                "step": 3,
                "from": {
                    "amount": format_amount(str(output_amt_without_aggregator)),
                    "token": underlying_symbol,
                    "name": underlying_name
                },
                "to": {
                    "token": "WETH",
                    "name": "Wrapped Ether"
                },
                "method": "CowSwap",
                "status": "failed",
                "error": cowswap_result["conversion_details"]["note"]
            })
        
        results["without_aggregator"] = {
            "amount_out": output_amt_without_aggregator,
            "price_impact": price_impact_without_aggregator,
            "steps": steps
        }
    except Exception as e:
        error_msg = str(e)
        print(f"✗ Failed without aggregator: {error_msg}")
        
        # Check if it's a MarketProportionTooHigh error and retry with doubled slippage
        if "MarketProportionTooHigh" in error_msg or "Market liquidity is likely insufficient" in error_msg:
            print(f"⚠️  Detected liquidity issue. Retrying with doubled slippage ({slippage * 2 * 100:.1f}%)...")
            try:
                quote_without_aggregator_retry = ConvertPTQuote(
                    market_address=market_address,
                    amount_in=amount,
                    production_address=receiver,
                    use_aggregator=False,
                    slippage=slippage * 2  # Double the slippage
                )
                output_amt_without_aggregator_retry = quote_without_aggregator_retry.get_amount_out()
                price_impact_without_aggregator_retry = quote_without_aggregator_retry.get_price_impact()
                
                print(f"✓ Retry successful! Output amount: {format_amount(str(output_amt_without_aggregator_retry))} {underlying_symbol}")
                print(f"Price impact: {price_impact_without_aggregator_retry * 100:.4f}%")
                
                # Get CowSwap quote for converting underlying to WETH
                print("\nGetting CowSwap quote for final conversion...")
                cowswap_result_retry = get_quote(
                    network=network,
                    sell_token=underlying_token,
                    buy_token=COMMON_TOKENS[network]["WETH"]["address"],
                    amount=str(output_amt_without_aggregator_retry),
                    token_decimals=18,
                    token_symbol=underlying_symbol
                )
                
                steps_retry = [
                    {
                        "step": 1,
                        "from": {
                            "amount": format_amount(str(amount)),
                            "token": pt_symbol,
                            "name": pt_name
                        },
                        "to": {
                            "amount": format_amount(str(output_amt_without_aggregator_retry)),
                            "token": sy_symbol,
                            "name": sy_name
                        },
                        "method": "Direct Pendle API (Retry with 2x slippage)",
                        "price_impact": f"{price_impact_without_aggregator_retry * 100:.4f}%"
                    },
                    {
                        "step": 2,
                        "from": {
                            "amount": format_amount(str(output_amt_without_aggregator_retry)),
                            "token": sy_symbol,
                            "name": sy_name
                        },
                        "to": {
                            "amount": format_amount(str(output_amt_without_aggregator_retry)),
                            "token": underlying_symbol,
                            "name": underlying_name
                        },
                        "method": "1:1 conversion"
                    }
                ]
                
                # Add CowSwap step if quote is successful
                if cowswap_result_retry["quote"]:
                    weth_amount_retry = int(cowswap_result_retry["quote"]["quote"]["buyAmount"])
                    cowswap_price_impact_retry = float(cowswap_result_retry["conversion_details"].get("price_impact", "0"))
                    if isinstance(cowswap_price_impact_retry, str) and cowswap_price_impact_retry == "N/A":
                        cowswap_price_impact_retry = 0
                        
                    print(f"CowSwap quote successful! Output amount: {format_amount(str(weth_amount_retry))} WETH")
                    print(f"CowSwap price impact: {cowswap_price_impact_retry:.4f}%")
                        
                    steps_retry.append({
                        "step": 3,
                        "from": {
                            "amount": format_amount(str(output_amt_without_aggregator_retry)),
                            "token": underlying_symbol,
                            "name": underlying_name
                        },
                        "to": {
                            "amount": format_amount(str(weth_amount_retry)),
                            "token": "WETH",
                            "name": "Wrapped Ether"
                        },
                        "method": "CowSwap",
                        "price_impact": f"{cowswap_price_impact_retry:.4f}%",
                        "status": "success"
                    })
                    # Update final amount to WETH amount
                    output_amt_without_aggregator_retry = weth_amount_retry
                else:
                    print(f"✗ CowSwap quote failed: {cowswap_result_retry['conversion_details']['note']}")
                    steps_retry.append({
                        "step": 3,
                        "from": {
                            "amount": format_amount(str(output_amt_without_aggregator_retry)),
                            "token": underlying_symbol,
                            "name": underlying_name
                        },
                        "to": {
                            "token": "WETH",
                            "name": "Wrapped Ether"
                        },
                        "method": "CowSwap",
                        "status": "failed",
                        "error": cowswap_result_retry["conversion_details"]["note"]
                    })
                
                results["without_aggregator"] = {
                    "amount_out": output_amt_without_aggregator_retry,
                    "price_impact": price_impact_without_aggregator_retry,
                    "steps": steps_retry
                }
            except Exception as retry_e:
                print(f"✗ Retry also failed: {str(retry_e)}")
                results["without_aggregator"] = {
                    "error": f"Original: {error_msg} | Retry: {str(retry_e)}",
                    "steps": []
                }
        else:
            results["without_aggregator"] = {
                "error": error_msg,
                "steps": []
            }
    
    # Determine best result
    print("\n=== Determining Best Result ===")
    best_result = None
    best_amount = 0
    
    if "amount_out" in results["with_aggregator"]:
        best_result = "with_aggregator"
        best_amount = results["with_aggregator"]["amount_out"]
        print(f"Method 1 (with aggregator) output: {format_amount(str(best_amount))} WETH")
    
    if "amount_out" in results["without_aggregator"]:
        print(f"Method 2 (without aggregator) output: {format_amount(str(results['without_aggregator']['amount_out']))} WETH")
        if results["without_aggregator"]["amount_out"] > best_amount:
            best_result = "without_aggregator"
            best_amount = results["without_aggregator"]["amount_out"]
    
    print(f"\nBest method: {best_result}")
    print(f"Best amount: {format_amount(str(best_amount))} WETH")
    
    # Create final conversion summary
    conversion_summary = {
        "market": market_name,
        "best_method": best_result,
        "best_amount": format_amount(str(best_amount)) if best_amount > 0 else None,
        "methods": {
            "with_aggregator": {
                "success": "amount_out" in results["with_aggregator"],
                "steps": results["with_aggregator"]["steps"]
            },
            "without_aggregator": {
                "success": "amount_out" in results["without_aggregator"],
                "steps": results["without_aggregator"]["steps"]
            }
        }
    }
    
    # Add error fields only if they exist
    if "error" in results["with_aggregator"]:
        conversion_summary["methods"]["with_aggregator"]["error"] = results["with_aggregator"]["error"]
    if "error" in results["without_aggregator"]:
        conversion_summary["methods"]["without_aggregator"]["error"] = results["without_aggregator"]["error"]
    
    print("\n=== Conversion Process Complete ===")
    return conversion_summary

if __name__ == "__main__":
    # Example usage
    market_address = "0x58612beb0e8a126735b19bb222cbc7fc2c162d2a"  # PT-ETH-30JUN24
    amount = 5000000000000000000  # 5 PT tokens in wei
    receiver = "0x66dbcee7fea3287b3356227d6f3dff3cefbc6f3c"  # Example receiver address
    
    try:
        print("\n=== PT CONVERSION PROCESS ===")
        print("============================")
        print(f"Market: {market_address}")
        print(f"Amount: {format_amount(str(amount))} PT")
        print(f"Receiver: {receiver}")
        print("=" * 50)
        
        # Get conversion summary
        result = convert_pt(
            market_address=market_address,
            amount=amount,
            receiver=receiver
        )
        
        # Display results for each method
        for method, data in result["methods"].items():
            print(f"\nMethod: {method}")
            print("-" * 50)
            
            if data["success"]:
                for step in data["steps"]:
                    print(f"\nStep {step['step']}: {step['from']['token']} -> {step['to']['token']}")
                    print(f"Input :  {step['from']['amount']} {step['from']['token']}")
                    if 'name' in step['from']:
                        print(f"        ({step['from']['name']})")
                    
                    print(f"Output:  {step['to']['amount']} {step['to']['token']}")
                    if 'name' in step['to']:
                        print(f"        ({step['to']['name']})")
                    
                    print(f"Method: {step['method']}")
                    if 'price_impact' in step:
                        print(f"Price impact: {step['price_impact']}")
                    print("-" * 50)
            else:
                print(f"✗ Failed: {data['error']}")
        
        print("\n=== FINAL SUMMARY ===")
        print("====================")
        print(f"Best method: {result['best_method']}")
        print(f"Best amount: {result['best_amount']}")
        print("\nFull details:")
        print(json.dumps(result, indent=2))
        print("====================\n")
            
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        print("\nFull error traceback:")
        import traceback
        traceback.print_exc() 