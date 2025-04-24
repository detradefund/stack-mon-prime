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
        # === Yield-bearing tokens ===
        # These tokens represent positions in protocols and have underlying assets
        "autoUSD": {
            "address": "0xa7569A44f348d3D70d8ad5889e50F78E33d80D35",
            "decimals": 18,
            "name": "Tokemak autoUSD",
            "symbol": "autoUSD",
            "protocol": "tokemak"  # Protocol identifier for balance aggregation
        },
        "sUSDS": {
            "address": "0xa3931d71877C0E7a3148CB7Eb4463524FEc27fbD",
            "decimals": 18,
            "name": "Savings USDS",
            "symbol": "sUSDS",
            "protocol": "sky",  # Protocol identifier for balance aggregation
            "underlying": {
                "USDS": {  # Underlying token that generates yield
                    "address": "0xdC035D45d973E3EC169d2276DDab16f1e407384F",
                    "decimals": 18,
                    "name": "USDS",
                    "symbol": "USDS"
                }
            }
        },
        "PT-eUSDE-29MAY2025": {
            "address": "0x50D2C7992b802Eef16c04FeADAB310f31866a545",
            "decimals": 18,
            "name": "Pendle PT Ethereal eUSDE 29MAY2025",
            "symbol": "PT-eUSDE-29MAY2025",
            "protocol": "pendle",
            "market": "0x85667e484a32d884010cf16427d90049ccf46e97",
            "underlying": {
                "eUSDe": {
                    "address": "0x90d2af7d622ca3141efa4d8f1f24d86e5974cc8f",
                    "decimals": 18,
                    "name": "Ethereal Pre-deposit Vault",
                    "symbol": "eUSDe"
                }
            },
            "expiry": 1748476800
        },
        "PT-cUSDO-19JUN2025": {
            "address": "0x933B9FfEE0Ad3Ef8E4DBb52688ea905826D73755",
            "decimals": 18,
            "name": "PT Compounding Open Dollar 19JUN2025",
            "symbol": "PT-cUSDO-19JUN2025",
            "protocol": "pendle",  # Protocol identifier for yield calculation
            "market": "0xa77c0de4d26b7c97d1d42abd6733201206122e25",  # Required for Pendle market interactions
            "underlying": {
                "cUSDO": {  # Token generating yield in Pendle market
                    "address": "0xaD55aebc9b8c03FC43cd9f62260391c13c23e7c0",
                    "decimals": 18,
                    "name": "Compounding Open Dollar",
                    "symbol": "cUSDO"
                }
            },
            "expiry":1750291200
        },
        "scrvUSD": {
            "address": "0x0655977FEb2f289A4aB78af67BAB0d17aAb84367",
            "decimals": 18,
            "name": "Savings crvUSD",
            "symbol": "scrvUSD"
        },

        # === Base stablecoins ===
        # Core stablecoins used for value calculation
        "USDC": {
            "address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            "decimals": 6,
            "name": "USD Coin",
            "symbol": "USDC"
        },
        "USDS": {
            "address": "0xdC035D45d973E3EC169d2276DDab16f1e407384F",
            "decimals": 18,
            "name": "USDS",
            "symbol": "USDS"
        },
        "eUSDe": {  # Add eUSDe in standard format
            "address": "0x90d2af7d622ca3141efa4d8f1f24d86e5974cc8f",  # Address correction
            "decimals": 18,
            "name": "Ethereal Pre-deposit Vault",
            "symbol": "eUSDe"
        },
        "cUSDO": {  # Add cUSDO in standard format
            "address": "0xaD55aebc9b8c03FC43cd9f62260391c13c23e7c0",
            "decimals": 18,
            "name": "Compounding Open Dollar",
            "symbol": "cUSDO"
        },
        "crvUSD": {
            "address": "0xf939e0a03fb07f59a73314e73794be0e57ac1b4e",
            "decimals": 18,
            "name": "Curve.Fi USD Stablecoin",
            "symbol": "crvUSD"
        },
        "GHO": {
            "address": "0x40D16FC0246aD3160Ccc09B8D0D3A2cD28aE6C2f",
            "decimals": 18,
            "name": "GHO Token",
            "symbol": "GHO"
        },
        "fxUSD": {
            "address": "0x085780639CC2cACd35E474e71f4d000e2405d8f6",
            "decimals": 18,
            "name": "f(x) USD",
            "symbol": "fxUSD"
        },
        "USR": {
            "address": "0x66a1E37c9b0eAddca17d3662D6c05F4DECf3e110",
            "decimals": 18,
            "name": "Resolv USD",
            "symbol": "USR"
        },

        # === Protocol & Reward tokens ===
        # Tokens used for protocol governance and rewards
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
        "CVX": {
            "address": "0x4e3FBD56CD56c3e72c1403e103b45Db9da5B9D2B",
            "decimals": 18,
            "name": "Convex Token",
            "symbol": "CVX"
        },
        "CRV": {
            "address": "0xD533a949740bb3306d119CC777fa900bA034cd52",
            "decimals": 18,
            "name": "Curve DAO Token",
            "symbol": "CRV"
        },
        "FXN": {
            "address": "0x365AccFCa291e7D3914637ABf1F7635dB165Bb09",
            "decimals": 18,
            "name": "FXN Token",
            "symbol": "FXN"
        },
        "wstETH": {
            "address": "0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0",
            "decimals": 18,
            "name": "Wrapped liquid staked Ether 2.0",
            "symbol": "wstETH"
        }
    },
    "base": {
        # === Yield-bearing tokens ===
        "sUSDS": {
            "address": "0x5875eEE11Cf8398102FdAd704C9E96607675467a",
            "decimals": 18,
            "name": "Savings USDS",
            "symbol": "sUSDS",
            "protocol": "sky",
            "underlying": {
                "USDS": {
                    "address": "0x820C137fa70C8691f0e44Dc420a5e53c168921Dc",
                    "decimals": 18,
                    "name": "USDS",
                    "symbol": "USDS"
                }
            }
        },
        "PT-USR-24APR2025": {
            "address": "0xec443e7E0e745348E500084892C89218B3ba4683",
            "decimals": 18,
            "name": "Pendle PT Resolv USD 24APR2025",
            "symbol": "PT-USR-24APR2025",
            "protocol": "pendle",
            "market": "0xe15578523937ed7f08e8f7a1fa8a021e07025a08",
            "underlying": {
                "USR": {
                    "address": "0x35E5dB674D8e93a03d814FA0ADa70731efe8a4b9",
                    "decimals": 18,
                    "name": "Resolve USD",
                    "symbol": "USR"
                }
            },
            "expiry": 1745452800
        },

        # === Base stablecoins ===
        "USDC": {
            "address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            "decimals": 6,
            "name": "USD Coin",
            "symbol": "USDC"
        },
        "USDS": {
            "address": "0x820C137fa70C8691f0e44Dc420a5e53c168921Dc",
            "decimals": 18,
            "name": "USDS",
            "symbol": "USDS"
        },
        "USR": {
            "address": "0x35E5dB674D8e93a03d814FA0ADa70731efe8a4b9",
            "decimals": 18,
            "name": "Resolve USD",
            "symbol": "USR"
        },
        "DTUSDC": {
            "address": "0x8092cA384D44260ea4feaf7457B629B8DC6f88F0",
            "decimals": 18,
            "name": "DeTrade Core USDC",
            "symbol": "DTUSDC"
        }
    }
}