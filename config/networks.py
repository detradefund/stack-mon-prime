import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# RPC endpoints for supported networks
RPC_URLS = {
    "ethereum": os.getenv('ETHEREUM_RPC'),
    "base": os.getenv('BASE_RPC'),
}

# Chain IDs for network identification
CHAIN_IDS = {
    "ethereum": "1",
    "base": "8453"
}

# Complete network token configuration
# Tokens are organized in categories:
# 1. Yield-bearing tokens (with underlying assets and protocol info)
# 2. Base stablecoins
# 3. Other tokens (governance, rewards, etc.)
NETWORK_TOKENS = {
    "ethereum": {

        "PT-pufETH-26JUN2025": {
            "address": "0x9cFc9917C171A384c7168D3529Fc7e851a2E0d6D",
            "decimals": 18,
            "name": "PT Puffer ETH 26JUN2025",
            "symbol": "PT-pufETH-26JUN2025",
            "protocol": "pendle",
            "type": "yield-bearing",
            "expiry": 1750896000,
            "market": "0x58612beb0e8a126735b19bb222cbc7fc2c162d2a",
            "underlying": {
                "pufETH": {
                    "address": "0xd9a442856c234a39a81a089c06451ebaa4306a72",
                    "decimals": 18,
                    "symbol": "pufETH"
                }
            }
        },
        "WETH": {
            "address": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "decimals": 18,
            "name": "Wrapped Ether",
            "symbol": "WETH"
        },
        "stETH": {
            "address": "0xae7ab96520de3a18e5e111b5eaab095312d7fe84",
            "decimals": 18,
            "name": "Lido Staked Ether",
            "symbol": "stETH"
        },
        "USDC": {
            "address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            "decimals": 6,
            "name": "USD Coin",
            "symbol": "USDC"
        },
        "PENDLE": {
            "address": "0x808507121B80c02388fAd14726482e061B8da827",
            "decimals": 18,
            "name": "Pendle",
            "symbol": "PENDLE"
        },
        "TOKE": {
            "address": "0x2e9d63788249371f1DFC918a52f8d799F4a38C94",
            "decimals": 18,
            "name": "Tokemak",
            "symbol": "TOKE"
        }
    },
    "base": {
        "WETH": {
            "address": "0x4200000000000000000000000000000000000006",
            "decimals": 18,
            "name": "Wrapped Ether",
            "symbol": "WETH"
        },
        "USDC": {
            "address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            "decimals": 6,
            "name": "USD Coin",
            "symbol": "USDC"
        },
        "baseETH": {
            "address": "0xAADf01DD90aE0A6Bb9Eb908294658037096E0404",
            "decimals": 18,
            "name": "Tokemak baseETH",
            "symbol": "baseETH",
            "protocol": "tokemak",
            "type": "yield-bearing",
            "rewarder": "0xb592c1539AC22EdD9784eA4d6a22199C16314498"
        },
        "cbETH": {
            "address": "0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22",
            "decimals": 18,
            "name": "Coinbase Wrapped Staked ETH",
            "symbol": "cbETH",
            "type": "yield-bearing"
        },
        "CRV": {
            "address": "0x8Ee73c484A26e0A5df2Ee2a4960B789967dd0415",
            "decimals": 18,
            "name": "Curve DAO Token",
            "symbol": "CRV"
        },
        "crvUSD": {
            "address": "0x417Ac0e078398C154EdFadD9Ef675d30Be60Af93",
            "decimals": 18,
            "name": "Curve.Fi USD Stablecoin",
            "symbol": "crvUSD"
        }
    }
}