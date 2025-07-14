import requests
import json
from typing import Dict, Any, Optional

class EulerGraphQLClient:
    def __init__(self):
        self.endpoint = "https://api.goldsky.com/api/public/project_cm4iagnemt1wp01xn4gh1agft/subgraphs/euler-v2-mainnet/latest/gn"
        self.headers = {
            "Content-Type": "application/json",
        }
    
    def query_active_positions(self, address: str) -> Optional[Dict[str, Any]]:
        """
        Query the Subgraph for Active Positions
        Use the trackingActiveAccount query to get all positions and their associated vaults for a given address
        """
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
            "address": address
        }
        
        payload = {
            "query": query,
            "variables": variables
        }
        
        try:
            response = requests.post(
                self.endpoint,
                json=payload,
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            if "errors" in data:
                print(f"GraphQL errors: {data['errors']}")
                return None
                
            return data.get("data")
            
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON response: {e}")
            return None
    
    def format_position_data(self, data: Dict[str, Any]) -> None:
        """Format and display the position data"""
        if not data or not data.get("trackingActiveAccount"):
            print("No active positions found for this address")
            return
        
        account = data["trackingActiveAccount"]
        
        print(f"Active Positions for Address: {account['mainAddress']}")
        print("=" * 50)
        
        print(f"Deposits: {account.get('deposits', 'No deposits')}")
        print(f"Borrows: {account.get('borrows', 'No borrows')}")

def main():
    client = EulerGraphQLClient()
    
    # Example usage - replace with actual address
    test_address = "0x1234567890123456789012345678901234567890"  # Replace with real address
    
    print(f"Querying active positions for address: {test_address}")
    print(f"Endpoint: {client.endpoint}")
    print()
    
    result = client.query_active_positions(test_address)
    
    if result:
        client.format_position_data(result)
    else:
        print("Failed to retrieve data")

if __name__ == "__main__":
    main() 