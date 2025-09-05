import sys
from pathlib import Path
from typing import Dict, Any
import json
from decimal import Decimal
from web3 import Web3
import os
from dotenv import load_dotenv

# Add parent directory to PYTHONPATH
root_path = str(Path(__file__).parent.parent)
sys.path.append(root_path)

# Load environment variables
load_dotenv()

from config.networks import RPC_URLS

def get_pingu_balance_from_contract() -> str:
    """
    Get MON balance from Pingu PoolStore contract using getUserBalance
    """
    print("\n" + "="*50)
    print("PINGU BALANCE FROM CONTRACT")
    print("="*50)
    
    # Contract configuration
    POOL_STORE_ADDRESS = "0xD849497f08180d3f1a79397EF8ae4DBD05EC1a5c"
    PRODUCTION_ADDRESS = os.getenv('PRODUCTION_ADDRESS', '0x2EAc9dF8299e544b9d374Db06ad57AD96C7527c0')
    MON_ASSET_ADDRESS = "0x0000000000000000000000000000000000000000"  # Native MON
    
    # Initialize Web3 connection
    w3 = Web3(Web3.HTTPProvider(RPC_URLS['monad-testnet']))
    if not w3.is_connected():
        raise ConnectionError("Failed to connect to RPC endpoint")
    
    # Load PoolStore ABI
    pool_store_abi_path = Path(__file__).parent / "pool_store.json"
    with open(pool_store_abi_path, 'r') as f:
        pool_store_abi = json.load(f)
    
    # Create contract instance
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(POOL_STORE_ADDRESS),
        abi=pool_store_abi
    )
    
    try:
        # Call getUserBalance function
        balance = contract.functions.getUserBalance(
            Web3.to_checksum_address(MON_ASSET_ADDRESS),
            Web3.to_checksum_address(PRODUCTION_ADDRESS)
        ).call()
        
        balance_wei = str(balance)
        balance_formatted = Decimal(balance_wei) / Decimal(10**18)
        
        print(f"✓ Contract Address: {POOL_STORE_ADDRESS}")
        print(f"✓ Production Address: {PRODUCTION_ADDRESS}")
        print(f"✓ MON Asset Address: {MON_ASSET_ADDRESS}")
        print(f"✓ Balance: {balance_formatted:.6f} MON ({balance_wei} wei)")
        
        return balance_wei
        
    except Exception as e:
        print(f"❌ Error calling contract: {str(e)}")
        raise

def get_user_input() -> str:
    """
    Get MON balance from user input (fallback method)
    """
    print("\n" + "="*50)
    print("PINGU BALANCE INPUT (FALLBACK)")
    print("="*50)
    
    while True:
        try:
            user_input = input("Enter your MON balance in Pingu (e.g., 1.5 for 1.5 MON): ").strip()
            if not user_input:
                print("Please enter a valid number.")
                continue
            
            # Convert to Decimal to validate
            amount = Decimal(user_input)
            if amount < 0:
                print("Please enter a positive number.")
                continue
            
            # Convert to wei
            wei_amount = str(int(amount * Decimal(10**18)))
            print(f"✓ Balance set to: {amount} MON ({wei_amount} wei)")
            return wei_amount
            
        except (ValueError,):
            print("Please enter a valid number (e.g., 1.5, 0.1, 10)")
        except KeyboardInterrupt:
            print("\nOperation cancelled.")
            sys.exit(1)

def build_pingu_document() -> Dict[str, Any]:
    """
    Build Pingu document with balance from contract or manual input.
    First tries to get balance from PoolStore contract, falls back to manual input.
    """
    
    # Try to get MON balance from contract first
    try:
        mon_balance_wei = get_pingu_balance_from_contract()
    except Exception as e:
        print(f"⚠️  Could not get balance from contract: {str(e)}")
        print("Falling back to manual input...")
        mon_balance_wei = get_user_input()
    
    # ========================================
    # PINGU BALANCE CONFIGURATION
    # ========================================
    PINGU_BALANCES = {
        "MON": {
            "amount": mon_balance_wei,  # User input converted to wei
            "decimals": 18
        }
    }
    
    # Calculate totals
    total_mon = Decimal("0")
    total_usdc = Decimal("0")
    
    # For now, we'll use simple 1:1 conversion for demonstration
    # In a real implementation, you would use Crystal Price Indexer
    for token_name, token_data in PINGU_BALANCES.items():
        amount = Decimal(token_data["amount"]) / Decimal(10**token_data["decimals"])
        # Simple conversion (replace with actual price conversion)
        if token_name == "MON":
            # MON to MON conversion (1:1)
            mon_value = amount
            usdc_value = mon_value * Decimal("3.843")  # Example: 1 MON = 3.843 USDC
        else:
            mon_value = amount
            usdc_value = amount * Decimal("3.843")
        
        total_mon += mon_value
        total_usdc += usdc_value
    
    return {
        "protocols": {
            "pingu": {
                "MON": {
                    "amount": PINGU_BALANCES["MON"]["amount"],
                    "decimals": PINGU_BALANCES["MON"]["decimals"],
                    "formatted": f"{Decimal(PINGU_BALANCES['MON']['amount']) / Decimal(10**PINGU_BALANCES['MON']['decimals']):.6f}",
                    "value": {
                        "WMON": {
                            "amount": str(int(total_mon * Decimal(10**18))),
                            "conversion_details": {
                                "rate": "1.000000",
                                "source": "Manual"
                            }
                        },
                        "USDC": {
                            "amount": str(int(total_usdc * Decimal(10**6))),
                            "conversion_details": {
                                "rate": "3.843000",
                                "source": "Manual"
                            }
                        }
                    }
                },
                "totals": {
                    "mon": str(int(total_mon * Decimal(10**18))),
                    "usdc": str(int(total_usdc * Decimal(10**6))),
                    "formatted_mon": f"{total_mon:.6f}",
                    "formatted_usdc": f"{total_usdc:.2f}"
                }
            }
        }
    }

def main():
    """
    Main function to test the Pingu balance manager
    """
    try:
        print("🚀 Starting Pingu Balance Manager...")
        document = build_pingu_document()
        
        print("\n" + "="*50)
        print("PINGU DOCUMENT GENERATED")
        print("="*50)
        print(json.dumps(document, indent=2))
        
        # Save to file
        output_file = "pingu_balance_output.json"
        with open(output_file, 'w') as f:
            json.dump(document, f, indent=2)
        print(f"\n✓ Document saved to: {output_file}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
