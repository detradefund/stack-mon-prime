"""
Market mapper class to handle market data mapping and queries.
"""
import json
from datetime import datetime

class MarketMapper:
    def __init__(self, active_markets_path):
        """Initialize the market mapper with the path to active markets data."""
        self.active_markets_path = active_markets_path
        self._load_markets()

    def _load_markets(self):
        """Load active markets data from file."""
        try:
            with open(self.active_markets_path, 'r') as f:
                self.markets_data = json.load(f)
        except FileNotFoundError:
            self.markets_data = {"markets": {}}

    def get_market_by_address(self, network: str, address: str):
        """Get market information by its address."""
        if network not in self.markets_data.get("markets", {}):
            return None

        for market in self.markets_data["markets"][network].get("markets", []):
            if market.get("address", "").lower() == address.lower():
                return market
        return None

    def get_markets_by_underlying(self, network: str, underlying_address: str):
        """Get all markets for a specific underlying asset."""
        if network not in self.markets_data.get("markets", {}):
            return []

        markets = []
        for market in self.markets_data["markets"][network].get("markets", []):
            if market.get("underlyingAsset", "").lower() == underlying_address.lower():
                markets.append(market)
        return markets

    def get_active_markets(self, network: str):
        """Get all active markets for a network."""
        if network not in self.markets_data.get("markets", {}):
            return []
        return self.markets_data["markets"][network].get("markets", [])

    def get_markets_by_expiry(self, network: str, expiry_date: datetime):
        """Get all markets expiring on a specific date."""
        if network not in self.markets_data.get("markets", {}):
            return []

        markets = []
        for market in self.markets_data["markets"][network].get("markets", []):
            if market.get("expiry"):
                market_expiry = datetime.fromisoformat(market["expiry"].replace("Z", "+00:00"))
                if market_expiry.date() == expiry_date.date():
                    markets.append(market)
        return markets 