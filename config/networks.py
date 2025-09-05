import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# RPC endpoints for supported networks
RPC_URLS = {
    "monad-testnet": os.getenv('TESTNET_MONAD_RPC'),
}

# Chain IDs for network identification
CHAIN_IDS = {
    "monad-testnet": "1337"
}

# Complete network token configuration for Monad
NETWORK_TOKENS = {
    "monad-testnet": {
        "WMON": {
            "address": "0x760AfE86e5de5fa0Ee542fc7B7B713e1c5425701",
            "decimals": 18,
            "name": "Wrapped Monad",
            "symbol": "WMON"
        },
        "USDC": {
            "address": "0xf817257fed379853cDe0fa4F97AB987181B1E5Ea",
            "decimals": 6,
            "name": "USD Coin",
            "symbol": "USDC"
        },
        "WETH": {
            "address": "0xB5a30b0FDc5EA94A52fDc42e3E9760Cb8449Fb37",
            "decimals": 18,
            "name": "Wrapped Ether",
            "symbol": "WETH"
        },
        "WBTC": {
            "address": "0xcf5a6076cfa32686c0Df13aBaDa2b40dec133F1d",
            "decimals": 8,
            "name": "Wrapped Bitcoin",
            "symbol": "WBTC"
        },
        "SOL": {
            "address": "0x5387C85A4965769f6B0Df430638a1388493486F1",
            "decimals": 9,
            "name": "Solana",
            "symbol": "SOL"
        },
        "USDT": {
            "address": "0x88b8E2161DEDC77EF4ab7585569D2415a1C1055D",
            "decimals": 6,
            "name": "Tether USD",
            "symbol": "USDT"
        },
        "PINGU": {
            "address": "0xA2426cD97583939E79Cfc12aC6E9121e37D0904d",
            "decimals": 18,
            "name": "Pingu Token",
            "symbol": "PINGU"
        },
        "aprMON": {
            "address": "0xb2f82D0f38dc453D596Ad40A37799446Cc89274A",
            "decimals": 18,
            "name": "aprMON",
            "symbol": "aprMON"
        },
        "sMON": {
            "address": "0xe1d2439b75fb9746E7Bc6cB777Ae10AA7f7ef9c5",
            "decimals": 18,
            "name": "sMON",
            "symbol": "sMON"
        },
        "shMON": {
            "address": "0x3a98250F98Dd388C211206983453837C8365BDc1",
            "decimals": 18,
            "name": "shMON",
            "symbol": "shMON"
        },

    }
}

# Common tokens used across networks
COMMON_TOKENS = {
    "monad-testnet": {
        "WMON": {
            "address": "0x760AfE86e5de5fa0Ee542fc7B7B713e1c5425701",
            "decimals": 18,
            "name": "Wrapped Monad",
            "symbol": "WMON"
        }
    }
}

# Crystal pool configurations with specific scaling factors
CRYSTAL_POOLS = {
    "monad-testnet": {
        "MON/USDC": {
            "pool_address": "0xCd5455B24f3622A1CfEce944615AE5Bc8f36Ee18",
            "quote_address": "0xf817257fed379853cDe0fa4F97AB987181B1E5Ea",  # USDC
            "base_address": "0x760AfE86e5de5fa0Ee542fc7B7B713e1c5425701",   # WMON
            "scaling_factor": 10**3,
            "max_price": 100000,
            "description": "MON/USDC Crystal Pool"
        },
        "WETH/USDC": {
            "pool_address": "0x9fA48CFB43829A932A227E4d7996e310ccf40E9C",
            "quote_address": "0xf817257fed379853cDe0fa4F97AB987181B1E5Ea",  # USDC
            "base_address": "0xB5a30b0FDc5EA94A52fDc42e3E9760Cb8449Fb37",   # WETH
            "scaling_factor": 10**1,
            "max_price": 1000000,
            "description": "WETH/USDC Crystal Pool"
        },
        "WBTC/USDC": {
            "pool_address": "0x45f7db719367bbf9E508D3CeA401EBC62fc732A9",
            "quote_address": "0xf817257fed379853cDe0fa4F97AB987181B1E5Ea",  # USDC
            "base_address": "0xcf5a6076cfa32686c0Df13aBaDa2b40dec133F1d",   # WBTC
            "scaling_factor": 1,
            "max_price": 1000000,
            "description": "WBTC/USDC Crystal Pool"
        },
        "SOL/USDC": {
            "pool_address": "0x5a6f296032AaAE6737ed5896bC09D01dc2d42507",
            "quote_address": "0xf817257fed379853cDe0fa4F97AB987181B1E5Ea",  # USDC
            "base_address": "0x5387C85A4965769f6B0Df430638a1388493486F1",   # SOL
            "scaling_factor": 10**2,
            "max_price": 100000,
            "description": "SOL/USDC Crystal Pool"
        },
        "USDT/USDC": {
            "pool_address": "0xCF16582dC82c4C17fA5b54966ee67b74FD715fB5",
            "quote_address": "0xf817257fed379853cDe0fa4F97AB987181B1E5Ea",  # USDC
            "base_address": "0x88b8E2161DEDC77EF4ab7585569D2415a1C1055D",   # USDT
            "scaling_factor": 10**3,
            "max_price": 10000,
            "description": "USDT/USDC Crystal Pool"
        },
        "PINGU/MON": {
            "pool_address": "0x3829EdA9aA5Bb9077d31F995327886309712BBA2",
            "quote_address": "0x760AfE86e5de5fa0Ee542fc7B7B713e1c5425701",  # WMON
            "base_address": "0xA2426cD97583939E79Cfc12aC6E9121e37D0904d",   # PINGU
            "scaling_factor": 10**5,
            "max_price": 100000,
            "description": "PINGU/MON Crystal Pool"
        },
        "aprMON/MON": {
            "pool_address": "0x33C5Dc9091952870BD1fF47c89fA53D63f9729b6",
            "quote_address": "0x760AfE86e5de5fa0Ee542fc7B7B713e1c5425701",  # WMON
            "base_address": "0xb2f82D0f38dc453D596Ad40A37799446Cc89274A",   # aprMON
            "scaling_factor": 10**4,
            "max_price": 100000,
            "description": "aprMON/MON Crystal Pool"
        },
        "sMON/MON": {
            "pool_address": "0x97fa0031E2C9a21F0727bcaB884E15c090eC3ee3",
            "quote_address": "0x760AfE86e5de5fa0Ee542fc7B7B713e1c5425701",  # WMON
            "base_address": "0xe1d2439b75fb9746E7Bc6cB777Ae10AA7f7ef9c5",   # sMON
            "scaling_factor": 10**4,
            "max_price": 100000,
            "description": "sMON/MON Crystal Pool"
        },
        "shMON/MON": {
            "pool_address": "0xcB5ec6D6d0E49478119525E4013ff333Fc46B742",
            "quote_address": "0x760AfE86e5de5fa0Ee542fc7B7B713e1c5425701",  # WMON
            "base_address": "0x3a98250F98Dd388C211206983453837C8365BDc1",   # shMON
            "scaling_factor": 10**4,
            "max_price": 100000,
            "description": "shMON/MON Crystal Pool"
        },

    }
}