#!/usr/bin/env python3
"""
Test script for querying Euler v2 mainnet subgraph via Goldsky
"""

from query_active_positions import EulerGraphQLClient

def test_query_with_address():
    """Test the GraphQL query with a specific address"""
    client = EulerGraphQLClient()
    
    # Replace with actual Ethereum address you want to query
    test_address = input("Enter Ethereum address to query (or press Enter for test address): ").strip()
    
    if not test_address:
        # Use a test address (you can replace this with any valid Ethereum address)
        test_address = "0x1234567890123456789012345678901234567890"
    
    print(f"\n🔍 Querying Euler v2 mainnet for address: {test_address}")
    print(f"📡 Endpoint: {client.endpoint}")
    print("-" * 80)
    
    # Query active positions
    result = client.query_active_positions(test_address)
    
    if result:
        print("✅ Query successful!")
        print("\n📊 Raw Response:")
        print(result)
        print("\n" + "=" * 80)
        
        # Format and display the data
        client.format_position_data(result)
    else:
        print("❌ Query failed or returned no data")

def test_query_structure():
    """Test the GraphQL query structure without making a request"""
    client = EulerGraphQLClient()
    
    query = """
    query Accounts($address: ID!) {
      trackingActiveAccount(id: $address) {
        mainAddress
        deposits
        borrows
      }
    }
    """
    
    variables = {
        "address": "0x1234567890123456789012345678901234567890"
    }
    
    payload = {
        "query": query,
        "variables": variables
    }
    
    print("📋 GraphQL Query Structure:")
    print("-" * 40)
    print("Query:", query)
    print("\nVariables:", variables)
    print("\nPayload:", payload)

if __name__ == "__main__":
    print("🚀 Euler v2 GraphQL Query Tester")
    print("=" * 50)
    
    choice = input("Choose test type:\n1. Test query structure\n2. Test actual query\nEnter choice (1 or 2): ").strip()
    
    if choice == "1":
        test_query_structure()
    elif choice == "2":
        test_query_with_address()
    else:
        print("Invalid choice. Running both tests...")
        test_query_structure()
        print("\n" + "=" * 80 + "\n")
        test_query_with_address() 