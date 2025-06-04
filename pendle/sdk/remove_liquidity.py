"""
Module for handling Pendle remove-liquidity operations.
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
    return f"{eth:,.4f}"

@dataclass
class RemoveLiquidityQuote:
    """Class to handle remove-liquidity quotes from Pendle."""
    
    def __init__(
        self,
        market_address: str,
        amount_in: int,
        production_address: str,
        slippage: float = 0.05,  # 5% default slippage
    ):
        """
        Initialize the RemoveLiquidityQuote.
        
        Args:
            market_address: The address of the Pendle market
            amount_in: Amount of LP tokens to remove (in wei)
            production_address: The address that will receive the tokens
            slippage: Maximum acceptable slippage (default: 0.05 = 5%)
        """
        self.market_address = market_address
        self.amount_in = amount_in
        self.receiver = production_address
        self.slippage = slippage
        
        # Load market data
        market_data = self._load_market_data()
        
        # Get SY token and chain_id from market data
        self.token_out = market_data["tokens"]["sy"].split("-")[1]  # Remove chain_id prefix
        self.chain_id = int(market_data["chain_id"])
        self.enable_aggregator = False
        self.market_name = market_data["name"]  # Store market name
        
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
        Get a quote for removing liquidity.
        
        Returns:
            dict: The quote response containing amountOut, priceImpact, and transaction data
        """
        base_url = f"https://api-v2.pendle.finance/core/v1/sdk/{self.chain_id}/markets/{self.market_address}/remove-liquidity"
        
        params = {
            "receiver": self.receiver,
            "slippage": self.slippage,
            "enableAggregator": str(self.enable_aggregator).lower(),
            "amountIn": str(self.amount_in),
            "tokenOut": self.token_out
        }
        
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        
        return response.json()
    
    def get_amount_out(self) -> int:
        """
        Get the expected amount out from removing liquidity.
        
        Returns:
            int: The expected amount out in wei
        """
        quote = self.get_quote()
        return int(quote["data"]["amountOut"])
    
    def get_price_impact(self) -> float:
        """
        Get the price impact of the removal.
        
        Returns:
            float: The price impact as a decimal
        """
        quote = self.get_quote()
        return float(quote["data"]["priceImpact"])
    
    def get_transaction_data(self) -> dict:
        """
        Get the transaction data for executing the removal.
        
        Returns:
            dict: The transaction data including contract call parameters
        """
        quote = self.get_quote()
        return {
            "tx": quote["tx"],
            "tokenApprovals": quote["tokenApprovals"]
        }

def remove_liquidity(market_address: str, amount: int, receiver: str = None, slippage: float = 0.05) -> dict:
    """
    Simple function to get remove liquidity quote and transaction data.
    
    Args:
        market_address: The address of the Pendle market
        amount: Amount of LP tokens to remove (in wei)
        receiver: The address that will receive the tokens (optional)
        slippage: Maximum acceptable slippage (default: 0.05 = 5%)
        
    Returns:
        dict: Dictionary containing conversion summary
    """
    if receiver is None:
        raise ValueError("receiver address is required")
        
    quote = RemoveLiquidityQuote(
        market_address=market_address,
        amount_in=amount,
        production_address=receiver,
        slippage=slippage
    )
    
    # Get market data
    market_data = quote._load_market_data()
    market_name = market_data["name"]
    sy_token = market_data["tokens"]["sy"].split("-")[1]
    underlying_token = market_data["tokens"]["underlyingAsset"].split("-")[1]
    chain_id = market_data["chain_id"]
    
    # Get Web3 instance
    network = "ethereum" if chain_id == "1" else "base" if chain_id == "8453" else None
    if network is None:
        raise ValueError(f"Unsupported chain_id: {chain_id}")
    w3 = Web3(Web3.HTTPProvider(RPC_URLS[network]))
    
    # Get SY token info
    sy_contract = w3.eth.contract(address=w3.to_checksum_address(sy_token), abi=[
        {"inputs": [], "name": "symbol", "outputs": [{"internalType": "string", "name": "", "type": "string"}], "stateMutability": "view", "type": "function"},
        {"inputs": [], "name": "name", "outputs": [{"internalType": "string", "name": "", "type": "string"}], "stateMutability": "view", "type": "function"}
    ])
    sy_symbol = sy_contract.functions.symbol().call()
    sy_name = sy_contract.functions.name().call()
    
    # Get underlying token info
    underlying_contract = w3.eth.contract(address=w3.to_checksum_address(underlying_token), abi=[
        {"inputs": [], "name": "symbol", "outputs": [{"internalType": "string", "name": "", "type": "string"}], "stateMutability": "view", "type": "function"},
        {"inputs": [], "name": "name", "outputs": [{"internalType": "string", "name": "", "type": "string"}], "stateMutability": "view", "type": "function"},
        {"inputs": [], "name": "asset", "outputs": [{"internalType": "address", "name": "", "type": "address"}], "stateMutability": "view", "type": "function"},
        {"inputs": [{"internalType": "uint256", "name": "shares", "type": "uint256"}], "name": "convertToAssets", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"}
    ])
    underlying_symbol = underlying_contract.functions.symbol().call()
    underlying_name = underlying_contract.functions.name().call()
    
    # Get amounts
    output_amt = quote.get_amount_out()
    price_impact = quote.get_price_impact()
    
    # Get LP token info
    lp_contract = w3.eth.contract(address=w3.to_checksum_address(market_address), abi=[
        {"inputs": [], "name": "symbol", "outputs": [{"internalType": "string", "name": "", "type": "string"}], "stateMutability": "view", "type": "function"},
        {"inputs": [], "name": "name", "outputs": [{"internalType": "string", "name": "", "type": "string"}], "stateMutability": "view", "type": "function"}
    ])
    lp_symbol = lp_contract.functions.symbol().call()
    lp_name = lp_contract.functions.name().call()
    
    # Create conversion summary
    conversion_summary = {
        "market": market_name,
        "conversion_steps": [
            {
                "step": 1,
                "from": {
                    "amount": format_amount(str(amount)),
                    "token": lp_symbol,
                    "name": lp_name
                },
                "to": {
                    "amount": format_amount(str(output_amt)),
                    "token": sy_symbol,
                    "name": sy_name
                },
                "method": "Direct Pendle API",
                "price_impact": f"{price_impact * 100:.4f}%"
            },
            {
                "step": 2,
                "from": {
                    "amount": format_amount(str(output_amt)),
                    "token": sy_symbol,
                    "name": sy_name
                },
                "to": {
                    "amount": format_amount(str(output_amt)),
                    "token": underlying_symbol,
                    "name": underlying_name
                },
                "method": "1:1 conversion"
            }
        ]
    }
    
    # Special case for wsuperOETHb market
    if market_address.lower() == "0xecc2c994aa0c599a7f69a7cfb9106fe4dffb4341":
        actual_asset_address = underlying_contract.functions.asset().call()
        actual_asset_contract = w3.eth.contract(address=w3.to_checksum_address(actual_asset_address), abi=[
            {"inputs": [], "name": "symbol", "outputs": [{"internalType": "string", "name": "", "type": "string"}], "stateMutability": "view", "type": "function"},
            {"inputs": [], "name": "name", "outputs": [{"internalType": "string", "name": "", "type": "string"}], "stateMutability": "view", "type": "function"}
        ])
        actual_asset_symbol = actual_asset_contract.functions.symbol().call()
        actual_asset_name = actual_asset_contract.functions.name().call()
        actual_underlying_amount = underlying_contract.functions.convertToAssets(output_amt).call()
        
        # Add step 3 to conversion summary
        conversion_summary["conversion_steps"].append({
            "step": 3,
            "from": {
                "amount": format_amount(str(output_amt)),
                "token": underlying_symbol,
                "name": underlying_name
            },
            "to": {
                "amount": format_amount(str(actual_underlying_amount)),
                "token": actual_asset_symbol,
                "name": actual_asset_name
            },
            "method": "convertToAssets function"
        })
        
        # Get CowSwap quote after all steps are added
        cowswap_result = get_quote(
            network=network,
            sell_token=actual_asset_address,
            buy_token=COMMON_TOKENS[network]["WETH"]["address"],
            amount=str(actual_underlying_amount),
            token_decimals=18,
            token_symbol=actual_asset_name
        )
        
        if cowswap_result["quote"]:
            weth_amount = int(cowswap_result["quote"]["quote"]["buyAmount"])
            cowswap_price_impact = float(cowswap_result["conversion_details"].get("price_impact", "0"))
            if isinstance(cowswap_price_impact, str) and cowswap_price_impact == "N/A":
                cowswap_price_impact = 0
                
            conversion_summary["conversion_steps"].append({
                "step": 4,
                "from": {
                    "amount": format_amount(str(actual_underlying_amount)),
                    "token": actual_asset_symbol,
                    "name": actual_asset_name
                },
                "to": {
                    "amount": format_amount(str(weth_amount)),
                    "token": "WETH"
                },
                "method": "CowSwap",
                "price_impact": f"{cowswap_price_impact:.4f}%",
                "status": "success"
            })
        else:
            conversion_summary["conversion_steps"].append({
                "step": 4,
                "from": {
                    "amount": format_amount(str(actual_underlying_amount)),
                    "token": actual_asset_symbol,
                    "name": actual_asset_name
                },
                "to": {
                    "token": "WETH"
                },
                "method": "CowSwap",
                "status": "failed",
                "error": cowswap_result["conversion_details"]["note"]
            })
    
    return conversion_summary

if __name__ == "__main__":
    # Example usage
    market_address = "0xecc2c994aa0c599a7f69a7cfb9106fe4dffb4341"  # Example market address
    amount = 5000000000000000000  # 1 LP token in wei
    receiver = "0x66dbcee7fea3287b3356227d6f3dff3cefbc6f3c"  # Example receiver address
    
    try:
        print("\n=== LIQUIDITY REMOVAL PROCESS ===")
        print("=================================")
        
        # Get the conversion summary
        result = remove_liquidity(
            market_address=market_address,
            amount=amount,
            receiver=receiver
        )
        
        # Display each step in order
        for step in result['conversion_steps']:
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
            if 'status' in step:
                print(f"Status: {step['status']}")
            print("-" * 50)
        
        print("\n=== FINAL SUMMARY ===")
        print("====================")
        print(json.dumps(result, indent=2))
        print("====================\n")
            
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        print("\nFull error traceback:")
        import traceback
        traceback.print_exc() 