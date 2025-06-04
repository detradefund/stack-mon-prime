"""
Simple script to refresh Pendle markets data and fetch active markets.
"""
import json
import os
import requests
from datetime import datetime
from .market_mapper import MarketMapper

class PendleMarkets:
    def __init__(self):
        self.config_file = os.path.join(os.path.dirname(__file__), "markets.json")
        self.store_dir = os.path.join(os.path.dirname(__file__), "store")
        self.market_mapping_file = os.path.join(os.path.dirname(__file__), "market_mapping.json")
        os.makedirs(self.store_dir, exist_ok=True)
        self.config = self._load_config()
        self.active_markets_path = os.path.join(self.store_dir, "active_markets.json")
        # Initialize market_mapper only if active_markets.json exists
        self.market_mapper = None
        if os.path.exists(self.active_markets_path):
            self.market_mapper = MarketMapper(self.active_markets_path)
    
    def _load_config(self):
        """Load markets configuration"""
        with open(self.config_file, 'r') as f:
            return json.load(f)
    
    def get_market_data(self, chain_id: str, market_address: str):
        """Get market data from Pendle API"""
        url = f"https://api-v2.pendle.finance/core/v2/{chain_id}/markets/{market_address}/data"
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching data for {market_address}: {str(e)}")
            return None
    
    def update_market_data(self, chain_id: str, market_address: str):
        """Update and store market data"""
        data = self.get_market_data(chain_id, market_address)
        if not data:
            return
            
        store_data = {
            "last_updated": datetime.now().isoformat(),
            "chain_id": chain_id,
            "market_address": market_address,
            "data": data
        }
        
        filepath = os.path.join(self.store_dir, f"{chain_id}_{market_address}_market_data.json")
        with open(filepath, 'w') as f:
            json.dump(store_data, f, indent=2)
            
        print(f"✓ Updated {market_address}")

    def refresh_all_markets(self):
        """Refresh data for all markets in the configuration"""
        print("\nRefreshing configured markets...")
        for network, config in self.config.items():
            chain_id = config["chain_id"]
            print(f"\nNetwork: {network}")
            for market in config["markets"]:
                if market.get("active", True):  # Only update active markets
                    self.update_market_data(chain_id, market["address"])
        print("\nAll configured markets refreshed!")

    def fetch_active_markets(self):
        """Fetch all active markets from Pendle API"""
        print("\nFetching active markets from all networks...")
        active_markets = {}
        
        for network, config in self.config.items():
            chain_id = config["chain_id"]
            print(f"\nNetwork: {network}")
            url = f"https://api-v2.pendle.finance/core/v1/{chain_id}/markets/active"
            try:
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                data = response.json()
                active_markets[network] = data
                print(f"✓ Found {len(data.get('markets', []))} active markets")
            except Exception as e:
                print(f"Error fetching markets for {network}: {str(e)}")
                active_markets[network] = None
        
        # Save to store
        store_data = {
            "last_updated": datetime.now().isoformat(),
            "markets": active_markets
        }
        
        filepath = os.path.join(self.store_dir, "active_markets.json")
        with open(filepath, 'w') as f:
            json.dump(store_data, f, indent=2)
            
        print(f"\nActive markets data saved to {filepath}")
        
        # Initialize market mapper with new data
        self.market_mapper = MarketMapper(self.active_markets_path)
        
        return active_markets

    def create_market_mapping(self):
        """Create a unified market mapping with all market data"""
        print("\nCreating market mapping...")
        mapping = {
            "last_updated": datetime.now().isoformat(),
            "markets": {}
        }

        # Load active markets data
        active_markets_data = {"markets": {}}
        if os.path.exists(self.active_markets_path):
            try:
                with open(self.active_markets_path, 'r') as f:
                    active_markets_data = json.load(f)
            except Exception as e:
                print(f"Warning: Error loading active markets data: {str(e)}")

        for network, config in self.config.items():
            chain_id = config["chain_id"]
            for market in config["markets"]:
                if not market.get("active", True):
                    continue

                market_address = market["address"]
                market_name = market["name"]
                
                # Load market data
                market_data_file = os.path.join(self.store_dir, f"{chain_id}_{market_address}_market_data.json")
                try:
                    with open(market_data_file, 'r') as f:
                        market_data = json.load(f)
                except FileNotFoundError:
                    print(f"Warning: No data found for {market_name}")
                    continue

                # Get active market details if available
                active_market = None
                if network in active_markets_data.get("markets", {}):
                    for m in active_markets_data["markets"][network].get("markets", []):
                        if m.get("address", "").lower() == market_address.lower():
                            active_market = m
                            break

                # Extract data
                data = market_data.get("data", {})
                market_info = {
                    "name": market_name,
                    "address": market_address,
                    "network": network,
                    "chain_id": chain_id,
                    "total_supply": data.get("totalActiveSupply"),
                    "total_assets": data.get("totalSy"),
                    "apy": data.get("aggregatedApy"),
                    "implied_apy": data.get("impliedApy"),
                    "utilization_rate": data.get("totalActiveSupply") / data.get("totalSy") if data.get("totalSy") and data.get("totalSy") > 0 else None,
                    "total_volume_24h": data.get("tradingVolume", {}).get("usd"),
                    "tvl": data.get("liquidity", {}).get("usd"),
                    "price": data.get("assetPriceUsd"),
                    "underlying_price": data.get("assetPriceUsd"),
                    "pt_price": data.get("ptDiscount"),
                    "yt_price": data.get("ytFloatingApy")
                }

                # Add active market details if available
                if active_market:
                    market_info["expiry"] = active_market.get("expiry")
                    market_info["tokens"] = {
                        "pt": active_market.get("pt"),
                        "yt": active_market.get("yt"),
                        "sy": active_market.get("sy"),
                        "underlyingAsset": active_market.get("underlyingAsset")
                    }
                    if "details" in active_market:
                        market_info["details"] = active_market["details"]

                mapping["markets"][market_address] = market_info

        # Save mapping
        with open(self.market_mapping_file, 'w') as f:
            json.dump(mapping, f, indent=2)
            
        print(f"✓ Market mapping saved to {self.market_mapping_file}")

    def get_market_by_address(self, network: str, address: str):
        """Get market information by its address using the mapper."""
        if not self.market_mapper:
            return None
        return self.market_mapper.get_market_by_address(network, address)

    def get_markets_by_underlying(self, network: str, underlying_address: str):
        """Get all markets for a specific underlying asset using the mapper."""
        if not self.market_mapper:
            return None
        return self.market_mapper.get_markets_by_underlying(network, underlying_address)

    def get_active_markets(self, network: str):
        """Get all active markets for a network using the mapper."""
        if not self.market_mapper:
            return None
        return self.market_mapper.get_active_markets(network)

    def get_markets_by_expiry(self, network: str, expiry_date: datetime):
        """Get all markets expiring on a specific date using the mapper."""
        if not self.market_mapper:
            return None
        return self.market_mapper.get_markets_by_expiry(network, expiry_date)

def main():
    """Main function to refresh all markets data"""
    markets = PendleMarkets()
    
    # Refresh configured markets
    markets.refresh_all_markets()
    
    # Fetch active markets
    markets.fetch_active_markets()
    
    # Create market mapping
    markets.create_market_mapping()
    
    print("\nDone! All data has been updated.")

if __name__ == "__main__":
    main() 