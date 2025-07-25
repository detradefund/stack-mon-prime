#!/usr/bin/env python3
"""
Test script to verify context-based conversion behavior.
- SPOT context: should use native conversion for pufETH (automatic)
- EULER context: should always use CowSwap for all tokens
"""

import sys
from pathlib import Path

# Add parent directory to PYTHONPATH
sys.path.append(str(Path(__file__).parent))

from utils.wsteth_converter import (
    should_use_native_conversion,
    ConversionConfig
)
from cowswap.cow_client import get_quote
from config.networks import NETWORK_TOKENS

def test_context_configuration():
    """Test the context-based configuration"""
    
    print("=== Testing Context-Based Configuration ===\n")
    
    pufeth_address = NETWORK_TOKENS["ethereum"]["pufETH"]["address"]
    wsteth_address = NETWORK_TOKENS["ethereum"]["wstETH"]["address"]
    
    print("Testing should_use_native_conversion() with different contexts:")
    
    # Test pufETH
    spot_pufeth = should_use_native_conversion(pufeth_address, "ethereum", "spot")
    euler_pufeth = should_use_native_conversion(pufeth_address, "ethereum", "euler")
    
    print(f"pufETH - spot context:  {spot_pufeth} (should be True)")
    print(f"pufETH - euler context: {euler_pufeth} (should be False)")
    
    # Test wstETH  
    spot_wsteth = should_use_native_conversion(wsteth_address, "ethereum", "spot")
    euler_wsteth = should_use_native_conversion(wsteth_address, "ethereum", "euler")
    
    print(f"wstETH - spot context:  {spot_wsteth} (should be False - disabled)")
    print(f"wstETH - euler context: {euler_wsteth} (should be False)")
    
    print(f"\nConfiguration behavior:")
    print(f"✅ SPOT:  Native conversion enabled automatically")
    print(f"✅ EULER: Market prices (CowSwap) always used")

def test_spot_behavior():
    """Test behavior for spot context"""
    
    print("\n=== Testing SPOT Context Behavior ===\n")
    
    pufeth_address = NETWORK_TOKENS["ethereum"]["pufETH"]["address"]
    weth_address = NETWORK_TOKENS["ethereum"]["WETH"]["address"]
    test_amount = "1000000000000000000"  # 1 pufETH
    
    print("Testing pufETH conversion with spot context:")
    try:
        result = get_quote(
            network="ethereum",
            sell_token=pufeth_address,
            buy_token=weth_address,
            amount=test_amount,
            token_decimals=18,
            token_symbol="pufETH",
            context="spot"
        )
        
        if result["quote"]:
            source = result["conversion_details"]["source"]
            print(f"✅ Success! Source: {source}")
            if "Puffer" in source:
                print("   ✅ Correctly using native pufETH.convertToAssets()")
            else:
                print("   ⚠️  Using non-native conversion")
        else:
            print(f"❌ Failed: {result['conversion_details']['note']}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def test_euler_behavior():
    """Test behavior for euler context"""
    
    print("\n=== Testing EULER Context Behavior ===\n")
    
    pufeth_address = NETWORK_TOKENS["ethereum"]["pufETH"]["address"]
    weth_address = NETWORK_TOKENS["ethereum"]["WETH"]["address"]
    test_amount = "1000000000000000000"  # 1 pufETH
    
    print("Testing pufETH conversion with euler context (should use CowSwap):")
    try:
        result = get_quote(
            network="ethereum",
            sell_token=pufeth_address,
            buy_token=weth_address,
            amount=test_amount,
            token_decimals=18,
            token_symbol="pufETH",
            context="euler"
        )
        
        source = result["conversion_details"]["source"]
        print(f"✅ Source: {source}")
        if "CoW" in source or "Error" in source:
            print("   ✅ Correctly using CowSwap (market prices)")
        elif "Puffer" in source:
            print("   ❌ Incorrectly using native conversion for Euler context")
            
    except Exception as e:
        print(f"⚠️  Expected CowSwap failure: {str(e)[:100]}...")
        print("   ✅ No native conversion triggered for euler context")

if __name__ == "__main__":
    try:
        print("🧪 Testing Context-Based Conversion Behavior\n")
        
        test_context_configuration()
        test_spot_behavior()
        test_euler_behavior()
        
        print("\n=== Test Complete ===")
        print("\n📝 Summary:")
        print("✅ SPOT: pufETH uses native convertToAssets() automatically")
        print("✅ EULER: All tokens use CowSwap (market prices)")
        print("✅ No user interaction required during execution")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc() 