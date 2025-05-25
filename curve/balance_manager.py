"""
Curve Protocol balance manager.
Handles interactions with Curve pools and manages token balances.
"""

from typing import Dict, Optional, List, Tuple, Any
from decimal import Decimal
import json
from pathlib import Path
import sys
from web3 import Web3
import argparse
import time
from datetime import datetime
from cowswap.cow_client import get_quote

# Add parent directory to PYTHONPATH
sys.path.append(str(Path(__file__).parent.parent))

from config.networks import NETWORK_TOKENS, RPC_URLS
from utils.retry import APIRetry
from .pools import get_pool_address, get_gauge_address, get_lp_token_address, get_pool_abi

# Default address to check
DEFAULT_ADDRESS = "0x66DbceE7feA3287B3356227d6F3DfF3CeFbC6F3C"

class CurveBalanceManager:
    """
    Manages Curve Protocol interactions and balance tracking.
    """
    
    def __init__(self, network: str, w3: Web3):
        """
        Initialize the Curve balance manager.
        
        Args:
            network: Network identifier ('ethereum' or 'base')
            w3: Web3 instance for blockchain interaction
        """
        self.network = network
        self.w3 = w3
        self.network_tokens = NETWORK_TOKENS
        
    def get_gauge_balance(self, pool_name: str, user_address: str) -> Decimal:
        """
        Get the balance of LP tokens staked in a gauge.
        
        Args:
            pool_name: Name of the pool
            user_address: Address of the user
            
        Returns:
            Staked LP token balance
        """
        gauge_address = get_gauge_address(self.network, pool_name)
        
        # Load Child Liquidity Gauge ABI
        with open(Path(__file__).parent / "abis/Child Liquidity Gauge.json") as f:
            gauge_abi = json.load(f)
            
        gauge_contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(gauge_address),
            abi=gauge_abi
        )
        
        balance = gauge_contract.functions.balanceOf(
            self.w3.to_checksum_address(user_address)
        ).call()
        
        return Decimal(balance)
        
    def get_pool_balance(self, pool_name: str) -> Dict[str, Decimal]:
        """
        Get the current balance of tokens in a Curve pool.
        
        Args:
            pool_name: Name of the pool
            
        Returns:
            Dictionary of token balances in the pool
        """
        pool_address = get_pool_address(self.network, pool_name)
        abi_name = get_pool_abi(self.network, pool_name)
        
        # Load pool ABI
        with open(Path(__file__).parent / f"abis/{abi_name}.json") as f:
            pool_abi = json.load(f)
            
        pool_contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(pool_address),
            abi=pool_abi
        )
        
        # For Vyper contracts, we need to get balances one by one
        balances = {}
        for i in range(2):  # This pool has 2 tokens
            balance = pool_contract.functions.balances(i).call()
            if balance > 0:
                balances[str(i)] = Decimal(balance)
                
        return balances
        
    def get_token_price(self, token_address: str, pool_name: str) -> Decimal:
        """
        Get the price of a token from a Curve pool.
        
        Args:
            token_address: Address of the token
            pool_name: Name of the pool to use for price discovery
            
        Returns:
            Token price in USD
        """
        pool_address = get_pool_address(self.network, pool_name)
        abi_name = get_pool_abi(self.network, pool_name)
        
        # Load pool ABI
        with open(Path(__file__).parent / f"abis/{abi_name}.json") as f:
            pool_abi = json.load(f)
            
        pool_contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(pool_address),
            abi=pool_abi
        )
        
        virtual_price = pool_contract.functions.get_virtual_price().call()
        return Decimal(virtual_price) / Decimal(10**18)
        
    def get_lp_token_balance(self, pool_name: str, user_address: str) -> Decimal:
        """
        Get the LP token balance for a user in a specific pool.
        
        Args:
            pool_name: Name of the pool
            user_address: Address of the user
            
        Returns:
            LP token balance
        """
        lp_token_address = get_lp_token_address(self.network, pool_name)
        
        # Load ERC20 ABI
        with open(Path(__file__).parent / "abis/erc20.json") as f:
            erc20_abi = json.load(f)
            
        lp_token_contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(lp_token_address),
            abi=erc20_abi["abi"]
        )
        
        balance = lp_token_contract.functions.balanceOf(
            self.w3.to_checksum_address(user_address)
        ).call()
        
        return Decimal(balance)
        
    def get_pool_tvl(self, pool_name: str) -> Decimal:
        """
        Get the Total Value Locked (TVL) in a Curve pool.
        
        Args:
            pool_name: Name of the pool
            
        Returns:
            TVL in USD
        """
        pool_address = get_pool_address(self.network, pool_name)
        abi_name = get_pool_abi(self.network, pool_name)
        
        # Load pool ABI
        with open(Path(__file__).parent / f"abis/{abi_name}.json") as f:
            pool_abi = json.load(f)
            
        pool_contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(pool_address),
            abi=pool_abi
        )
        
        virtual_price = pool_contract.functions.get_virtual_price().call()
        total_supply = pool_contract.functions.totalSupply().call()
        
        return (Decimal(virtual_price) * Decimal(total_supply)) / Decimal(10**18)

    def get_lp_token_total_supply(self, pool_name: str) -> Decimal:
        """
        Get the total supply of LP tokens for a pool from the Child Liquidity Gauge.
        
        Args:
            pool_name: Name of the pool
            
        Returns:
            Total supply of LP tokens
        """
        gauge_address = get_gauge_address(self.network, pool_name)
        
        # Load Child Liquidity Gauge ABI
        with open(Path(__file__).parent / "abis/Child Liquidity Gauge.json") as f:
            gauge_abi = json.load(f)
            
        gauge_contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(gauge_address),
            abi=gauge_abi
        )
        
        total_supply = gauge_contract.functions.totalSupply().call()
        return Decimal(total_supply)

    def get_ownership_percentage(self, pool_name: str, user_address: str) -> Decimal:
        """
        Calculate the percentage of LP tokens owned by an address.
        
        Args:
            pool_name: Name of the pool
            user_address: Address of the user
            
        Returns:
            Percentage of LP tokens owned (0-100) with maximum precision
        """
        balance = self.get_gauge_balance(pool_name, user_address)
        total_supply = self.get_lp_token_total_supply(pool_name)
        
        if total_supply == 0:
            return Decimal('0')
            
        # Calculate ownership with maximum precision
        return (balance / total_supply) * Decimal('100')

    def get_pool_tokens(self, pool_name: str) -> List[Tuple[str, str]]:
        """
        Get the tokens in a Curve pool with their symbols.
        
        Args:
            pool_name: Name of the pool
            
        Returns:
            List of tuples containing (token_address, token_symbol)
        """
        pool_address = get_pool_address(self.network, pool_name)
        abi_name = get_pool_abi(self.network, pool_name)
        
        # Load pool ABI
        with open(Path(__file__).parent / f"abis/{abi_name}.json") as f:
            pool_abi = json.load(f)
            
        pool_contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(pool_address),
            abi=pool_abi
        )
        
        # Get token addresses from pool
        token_addresses = []
        for i in range(2):  # This pool has 2 tokens
            token_address = pool_contract.functions.coins(i).call()
            token_addresses.append(token_address)
            
        # Map addresses to symbols using NETWORK_TOKENS
        token_info = []
        for addr in token_addresses:
            addr_lower = addr.lower()
            symbol = "UNKNOWN"
            
            # Search for token in NETWORK_TOKENS
            for token_name, token_data in NETWORK_TOKENS[self.network].items():
                if token_data["address"].lower() == addr_lower:
                    symbol = token_data["symbol"]
                    break
                    
            token_info.append((addr, symbol))
            
        return token_info

    def get_pool_balances(self, pool_name: str) -> List[Tuple[str, str, Decimal]]:
        """
        Get the balances of tokens in a Curve pool.
        
        Args:
            pool_name: Name of the pool
            
        Returns:
            List of tuples containing (token_address, token_symbol, balance)
        """
        pool_address = get_pool_address(self.network, pool_name)
        abi_name = get_pool_abi(self.network, pool_name)
        
        # Load pool ABI
        with open(Path(__file__).parent / f"abis/{abi_name}.json") as f:
            pool_abi = json.load(f)
            
        pool_contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(pool_address),
            abi=pool_abi
        )
        
        # Get token addresses and balances
        token_info = []
        for i in range(2):  # This pool has 2 tokens
            token_address = pool_contract.functions.coins(i).call()
            balance = pool_contract.functions.balances(i).call()
            
            # Get token symbol
            addr_lower = token_address.lower()
            symbol = "UNKNOWN"
            decimals = 18  # Default to 18 decimals
            
            # Search for token in NETWORK_TOKENS
            for token_name, token_data in NETWORK_TOKENS[self.network].items():
                if token_data["address"].lower() == addr_lower:
                    symbol = token_data["symbol"]
                    decimals = token_data["decimals"]
                    break
            
            token_info.append((token_address, symbol, Decimal(balance) / Decimal(10**decimals)))
            
        return token_info

    def get_user_balances(self, pool_name: str, user_address: str) -> List[Tuple[str, str, Decimal]]:
        """
        Get the user's share of tokens in a Curve pool based on ownership percentage.
        Calculates exact token amounts with maximum precision.
        
        Args:
            pool_name: Name of the pool
            user_address: Address of the user
            
        Returns:
            List of tuples containing (token_address, token_symbol, user_balance) with maximum precision
        """
        # Get ownership percentage with maximum precision
        ownership = self.get_ownership_percentage(pool_name, user_address)
        pool_balances = self.get_pool_balances(pool_name)
        
        user_balances = []
        for addr, symbol, balance in pool_balances:
            # Calculate user's share with maximum precision
            # Divide by 100 since ownership is in percentage
            user_balance = (balance * ownership) / Decimal('100')
            user_balances.append((addr, symbol, user_balance))
            
        return user_balances

    def get_reward_tokens(self, pool_name: str) -> List[Tuple[str, str, int]]:
        """
        Get all reward tokens from the gauge by querying reward_tokens(index) until we get the zero address.
        Maps the token addresses to their symbols and decimals using NETWORK_TOKENS.
        
        Args:
            pool_name: Name of the pool
            
        Returns:
            List of tuples containing (token_address, token_symbol, decimals)
        """
        gauge_address = get_gauge_address(self.network, pool_name)
        
        # Load Child Liquidity Gauge ABI
        with open(Path(__file__).parent / "abis/Child Liquidity Gauge.json") as f:
            gauge_abi = json.load(f)
            
        gauge_contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(gauge_address),
            abi=gauge_abi
        )
        
        reward_tokens = []
        index = 0
        
        while True:
            try:
                token_address = gauge_contract.functions.reward_tokens(index).call()
                
                # Check if we've reached the end (zero address)
                if token_address == "0x0000000000000000000000000000000000000000":
                    break
                    
                # Map token address to symbol and decimals
                token_info = self._get_token_info(token_address)
                if token_info:
                    reward_tokens.append(token_info)
                    
                index += 1
            except Exception:
                # If we get an error, we've probably reached the end
                break
                
        return reward_tokens
        
    def _get_token_info(self, token_address: str) -> Optional[Tuple[str, str, int]]:
        """
        Helper method to get token information from NETWORK_TOKENS.
        
        Args:
            token_address: Address of the token
            
        Returns:
            Tuple of (token_address, token_symbol, decimals) or None if not found
        """
        addr_lower = token_address.lower()
        
        # Search for token in NETWORK_TOKENS
        for token_name, token_data in NETWORK_TOKENS[self.network].items():
            if token_data["address"].lower() == addr_lower:
                return (
                    token_address,
                    token_data["symbol"],
                    token_data["decimals"]
                )
                
        return None

    def get_claimable_rewards(self, pool_name: str, user_address: str) -> Dict[str, Any]:
        """
        Get claimable rewards for a user from the gauge.
        
        Args:
            pool_name: Name of the pool
            user_address: Address of the user
            
        Returns:
            Dictionary containing structured reward information
        """
        gauge_address = get_gauge_address(self.network, pool_name)
        
        print(f"\nChecking rewards for {user_address}")
        
        result = {
            "curve": {
                "base": {
                    pool_name: {
                        "amount": "0",
                        "decimals": 18,
                        "value": {},
                        "rewards": {},
                        "totals": {
                            "wei": 0,
                            "formatted": "0.000000"
                        }
                    }
                }
            }
        }
        
        try:
            # Load Child Liquidity Gauge ABI
            with open(Path(__file__).parent / "abis/Child Liquidity Gauge.json") as f:
                gauge_abi = json.load(f)
                
            gauge_contract = self.w3.eth.contract(
                address=self.w3.to_checksum_address(gauge_address),
                abi=gauge_abi
            )
            
            # Check gauge state
            is_killed = gauge_contract.functions.is_killed().call()
            working_balance = gauge_contract.functions.working_balances(
                self.w3.to_checksum_address(user_address)
            ).call()
            working_supply = gauge_contract.functions.working_supply().call()
            
            print(f"Gauge state: {'KILLED' if is_killed else 'ACTIVE'}")
            print(f"Working balance: {Decimal(working_balance) / Decimal(10**18):.6f} LP tokens")
            print(f"Working supply: {Decimal(working_supply) / Decimal(10**18):.6f} LP tokens")
            
            # Set LP token amount
            result["curve"]["base"][pool_name]["amount"] = str(working_balance)
            
            # Get user's pool tokens and their values
            user_balances = self.get_user_balances(pool_name, user_address)
            pool_total_eth = 0
            
            for addr, symbol, balance in user_balances:
                token_data = {
                    "amount": int(balance * Decimal(10**18)),
                    "decimals": 18
                }
                
                if symbol == "WETH":
                    token_data["value"] = {
                        "ETH": {
                            "amount": int(balance * Decimal(10**18)),
                            "decimals": 18,
                            "conversion_details": {
                                "source": "Direct",
                                "price_impact": "0",
                                "rate": "1.000000",
                                "fee_percentage": "0.0000%",
                                "fallback": False,
                                "note": "Direct 1:1 conversion"
                            }
                        }
                    }
                    token_data["totals"] = {
                        "wei": int(balance * Decimal(10**18)),
                        "formatted": f"{balance:.6f}"
                    }
                    pool_total_eth += int(balance * Decimal(10**18))
                else:
                    # Get quote for other tokens
                    quote_result = self.get_quote_with_fallback(
                        addr,
                        int(balance * Decimal(10**18)),
                        18,
                        symbol
                    )
                    if quote_result:
                        eth_value = quote_result["amount"]
                        token_data["value"] = {
                            "ETH": quote_result
                        }
                        token_data["totals"] = {
                            "wei": eth_value,
                            "formatted": f"{eth_value/1e18:.6f}"
                        }
                        pool_total_eth += eth_value
                
                result["curve"]["base"][pool_name]["value"][symbol] = token_data
            
            rewards_total = 0
            
            # First check CRV rewards
            try:
                claimable = gauge_contract.functions.claimable_tokens(
                    self.w3.to_checksum_address(user_address)
                ).call()
                
                crv_decimal = Decimal(claimable) / Decimal(10**18)
                if crv_decimal > 0:
                    crv_address = "0x8Ee73c484A26e0A5df2Ee2a4960B789967dd0415"  # CRV address on Base
                    
                    # Get CRV price in ETH using CoWSwap
                    quote_result = self.get_quote_with_fallback(
                        crv_address, claimable, 18, "CRV"
                    )
                    
                    if quote_result:
                        eth_value = quote_result["amount"]
                        result["curve"]["base"][pool_name]["rewards"]["CRV"] = {
                            "amount": claimable,
                            "decimals": 18,
                            "value": {
                                "ETH": quote_result
                            },
                            "totals": {
                                "wei": eth_value,
                                "formatted": f"{eth_value/1e18:.6f}"
                            }
                        }
                        rewards_total += eth_value
                    
            except Exception as e:
                print(f"Error checking CRV rewards: {str(e)}")
            
            # Then check other rewards
            try:
                reward_count = gauge_contract.functions.reward_count().call()
                
                for i in range(reward_count):
                    try:
                        token_address = gauge_contract.functions.reward_tokens(i).call()
                        
                        # Skip CRV token as we already checked it
                        if token_address.lower() == "0x8Ee73c484A26e0A5df2Ee2a4960B789967dd0415".lower():
                            continue
                        
                        # Get reward data
                        reward_data = gauge_contract.functions.reward_data(
                            self.w3.to_checksum_address(token_address)
                        ).call()
                        
                        # Get claimable amount
                        claimable = gauge_contract.functions.claimable_reward(
                            self.w3.to_checksum_address(user_address),
                            self.w3.to_checksum_address(token_address)
                        ).call()
                        
                        # Get token info
                        token_info = self._get_token_info(token_address)
                        if token_info and claimable > 0:
                            addr, symbol, decimals = token_info
                            
                            # Get token price in ETH using CoWSwap
                            quote_result = self.get_quote_with_fallback(
                                addr, claimable, decimals, symbol
                            )
                            
                            if quote_result:
                                eth_value = quote_result["amount"]
                                result["curve"]["base"][pool_name]["rewards"][symbol] = {
                                    "amount": claimable,
                                    "decimals": decimals,
                                    "value": {
                                        "ETH": quote_result
                                    },
                                    "totals": {
                                        "wei": eth_value,
                                        "formatted": f"{eth_value/1e18:.6f}"
                                    }
                                }
                                rewards_total += eth_value
                                
                    except Exception as e:
                        print(f"Error checking reward token {i}: {str(e)}")
                        continue
                        
            except Exception as e:
                print(f"Error checking other rewards: {str(e)}")
                
            # Update totals (pool tokens + rewards)
            total_eth_value = pool_total_eth + rewards_total
            result["curve"]["base"][pool_name]["totals"] = {
                "wei": total_eth_value,
                "formatted": f"{total_eth_value/1e18:.6f}"
            }
            
            # Add protocol total
            if total_eth_value > 0:
                result["curve"]["totals"] = {
                    "wei": total_eth_value,
                    "formatted": f"{total_eth_value/1e18:.6f}"
                }
                
        except Exception as e:
            print(f"Error loading gauge: {str(e)}")
            
        return result

    def get_quote_with_fallback(self, token_address: str, amount: int, decimals: int, symbol: str) -> Dict[str, Any]:
        """
        Gets ETH conversion quote for tokens.
        Uses the centralized quote logic from cow_client.py
        """
        print(f"\nAttempting to get quote for {symbol}:")
        
        result = get_quote(
            network="base",
            sell_token=token_address,
            buy_token=self.network_tokens["base"]["WETH"]["address"],
            amount=str(int(amount)),
            token_decimals=decimals,
            token_symbol=symbol
        )

        if result["quote"]:
            return {
                "amount": int(result["quote"]["quote"]["buyAmount"]),
                "decimals": 18,
                "conversion_details": result["conversion_details"]
            }
        
        return {
            "amount": 0,
            "decimals": 18,
            "conversion_details": result["conversion_details"]
        }

    def prepare_mint_transaction(self, pool_name: str) -> dict:
        """
        Prepare the transaction to mint CRV rewards.
        
        Args:
            pool_name: Name of the pool
            
        Returns:
            Transaction parameters that can be used to send the transaction
        """
        gauge_address = get_gauge_address(self.network, pool_name)
        
        # Load Factory ABI for CRV rewards
        with open(Path(__file__).parent / "abis/Child Liquidity Gauge Factory.json") as f:
            factory_abi = json.load(f)
            
        factory_address = "0xabC000d88f23Bb45525E447528DBF656A9D55bf5"
        factory_contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(factory_address),
            abi=factory_abi
        )
        
        # Build the transaction
        transaction = factory_contract.functions.mint(
            self.w3.to_checksum_address(gauge_address)
        ).build_transaction({
            'from': self.w3.eth.accounts[0],  # This will need to be replaced with the actual sender
            'gas': 200000,  # Gas limit
            'gasPrice': self.w3.eth.gas_price,
            'nonce': self.w3.eth.get_transaction_count(self.w3.eth.accounts[0])
        })
        
        return transaction

    def simulate_mint(self, pool_name: str, user_address: str) -> None:
        """
        Simulate the mint function call to see what it would do.
        
        Args:
            pool_name: Name of the pool
            user_address: Address of the user
        """
        gauge_address = get_gauge_address(self.network, pool_name)
        
        print(f"\nSimulating mint call:")
        print(f"Gauge address: {gauge_address}")
        print(f"User address: {user_address}")
        
        # Load Factory ABI for CRV rewards
        with open(Path(__file__).parent / "abis/Child Liquidity Gauge Factory.json") as f:
            factory_abi = json.load(f)
            
        factory_address = "0xabC000d88f23Bb45525E447528DBF656A9D55bf5"
        factory_contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(factory_address),
            abi=factory_abi
        )
        
        print(f"Factory address: {factory_address}")
        
        try:
            # Simulate the mint call with the same parameters as the real transaction
            print("\nSimulating mint function...")
            result = factory_contract.functions.mint(
                self.w3.to_checksum_address(gauge_address)
            ).call({
                'from': self.w3.to_checksum_address(user_address),
                'chainId': 8453  # Base
            })
            
            print(f"Simulation result: {result}")
            
            # Check minted amount after simulation
            crv_minted = factory_contract.functions.minted(
                self.w3.to_checksum_address(user_address),
                self.w3.to_checksum_address(gauge_address)
            ).call()
            
            print(f"CRV that would be minted: {Decimal(crv_minted) / Decimal(10**18)}")
            
        except Exception as e:
            print(f"Error simulating mint: {str(e)}")
            print(f"Error type: {type(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")

def main():
    """
    Main function to test the Curve balance manager.
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Check Curve gauge balance')
    parser.add_argument('address', type=str, nargs='?', default=DEFAULT_ADDRESS,
                      help='Address to check (default: ' + DEFAULT_ADDRESS + ')')
    args = parser.parse_args()
    
    # Initialize Web3 connection to Base using RPC from .env
    w3 = Web3(Web3.HTTPProvider(RPC_URLS["base"]))
    
    if not w3.is_connected():
        print("Failed to connect to Base network")
        return
        
    # Initialize balance manager
    manager = CurveBalanceManager("base", w3)
    
    try:
        print("\n" + "="*80)
        print("CURVE BALANCE MANAGER")
        print("="*80)
        
        # Get gauge balance for cbeth-f pool
        balance = manager.get_gauge_balance("cbeth-f", args.address)
        total_supply = manager.get_lp_token_total_supply("cbeth-f")
        ownership_percentage = manager.get_ownership_percentage("cbeth-f", args.address)
        pool_tokens = manager.get_pool_tokens("cbeth-f")
        pool_balances = manager.get_pool_balances("cbeth-f")
        user_balances = manager.get_user_balances("cbeth-f", args.address)
        
        print(f"\nCurve.fi cbeth-f Gauge Balance:")
        print(f"Address: {args.address}")
        print(f"Balance: {balance / Decimal(10**18):.6f} LP tokens")
        print(f"Total Supply: {total_supply / Decimal(10**18):.6f} LP tokens")
        print(f"Ownership: {ownership_percentage:.6f}%")
        
        print("\nPool Tokens:")
        for addr, symbol in pool_tokens:
            print(f"- {symbol}: {addr}")
            
        print("\nPool Balances:")
        for addr, symbol, balance in pool_balances:
            print(f"- {symbol}:")
            print(f"  Amount: {balance:.6f} {symbol}")
            
            # Convert to ETH value
            if symbol == "WETH":
                print(f"  Value: {balance:.6f} ETH (1:1 conversion)")
            else:
                # Get quote for other tokens
                quote_result = manager.get_quote_with_fallback(
                    addr,
                    int(balance * Decimal(10**18)),  # Convert to wei
                    18,  # Assuming 18 decimals
                    symbol
                )
                if quote_result:
                    eth_value = quote_result["amount"]
                    print(f"  Value: {Decimal(eth_value) / Decimal(10**18):.6f} ETH")
                    if "conversion_details" in quote_result:
                        conv_details = quote_result["conversion_details"]
                        print(f"  Conversion Details:")
                        print(f"    Source: {conv_details['source']}")
                        print(f"    Rate: {conv_details['rate']}")
                        print(f"    Fee: {conv_details['fee_percentage']}%")
                        if conv_details.get('note'):
                            print(f"    Note: {conv_details['note']}")
            
        # Get and display claimable rewards
        print("\nClaimable Rewards:")
        rewards = manager.get_claimable_rewards("cbeth-f", args.address)
        
        # Display rewards in a structured format
        if rewards["curve"]["base"]["cbeth-f"]["rewards"]:
            for symbol, reward_data in rewards["curve"]["base"]["cbeth-f"]["rewards"].items():
                amount = reward_data["amount"]
                decimals = reward_data["decimals"]
                eth_value = reward_data["totals"]["wei"]
                
                print(f"\n{symbol} Rewards:")
                print(f"  Amount: {Decimal(amount) / Decimal(10**decimals):.6f} {symbol}")
                print(f"  Value: {Decimal(eth_value) / Decimal(10**18):.6f} ETH")
                
                if "value" in reward_data and "ETH" in reward_data["value"]:
                    conv_details = reward_data["value"]["ETH"]["conversion_details"]
                    print(f"  Conversion Details:")
                    print(f"    Source: {conv_details['source']}")
                    print(f"    Rate: {conv_details['rate']}")
                    print(f"    Fee: {conv_details['fee_percentage']}%")
                    if conv_details.get('note'):
                        print(f"    Note: {conv_details['note']}")
            
            # Display total rewards value
            total_wei = rewards["curve"]["base"]["cbeth-f"]["totals"]["wei"]
            print(f"\nTotal Rewards Value: {Decimal(total_wei) / Decimal(10**18):.6f} ETH")
        else:
            print("No claimable rewards found")
            
        # Get pool and gauge addresses for reference
        pool_address = get_pool_address("base", "cbeth-f")
        gauge_address = get_gauge_address("base", "cbeth-f")
        lp_token_address = get_lp_token_address("base", "cbeth-f")
        
        print("\nContract Addresses:")
        print(f"Pool: {pool_address}")
        print(f"Gauge: {gauge_address}")
        print(f"LP Token: {lp_token_address}")
        
        # Display final JSON document
        print("\n" + "="*80)
        print("FINAL RESULT:")
        print("="*80 + "\n")
        print(json.dumps(rewards, indent=2))
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 