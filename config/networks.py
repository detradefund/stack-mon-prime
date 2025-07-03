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
        "pufETH": {
            "address": "0xd9a442856c234a39a81a089c06451ebaa4306a72",
            "decimals": 18,
            "name": "Puffer Finance ETH",
            "symbol": "pufETH"
        },
        "wstETH": {
            "address": "0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0",
            "decimals": 18,
            "name": "Wrapped Staked Ether",
            "symbol": "wstETH"
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
        },
        "CRV": {
            "address": "0xD533a949740bb3306d119CC777fa900bA034cd52",
            "decimals": 18,
            "name": "Curve DAO Token",
            "symbol": "CRV"
        }
    },
    "base": {
        "WETH": {
            "address": "0x4200000000000000000000000000000000000006",
            "decimals": 18,
            "name": "Wrapped Ether",
            "symbol": "WETH"
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
        "superOETHb": {
            "address": "0xDBFeFD2e8460a6Ee4955A68582F85708BAEA60A3",
            "decimals": 18,
            "name": "Super OETHb",
            "symbol": "superOETHb"
        },
        "PENDLE": {
            "address": "0xA99F6e6785Da0F5d6fB42495Fe424BCE029Eeb3E",
            "decimals": 18,
            "name": "Pendle",
            "symbol": "PENDLE"
        },
        "CRV": {
            "address": "0x8Ee73c484A26e0A5df2Ee2a4960B789967dd0415",
            "decimals": 18,
            "name": "Curve DAO Token",
            "symbol": "CRV"
        }
    }
}

# Common tokens used across networks
COMMON_TOKENS = {
    "ethereum": {
        "WETH": {
            "address": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "decimals": 18,
            "name": "Wrapped Ether",
            "symbol": "WETH"
        }
    },
    "base": {
        "WETH": {
            "address": "0x4200000000000000000000000000000000000006",
            "decimals": 18,
            "name": "Wrapped Ether",
            "symbol": "WETH"
        }
    }
}