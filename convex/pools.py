"""
Configuration for all Curve pools used in the system
"""

POOLS = {
    "pxETHstETH": {
        "gauge": "0x633556C8413FCFd45D83656290fF8d64EE41A7c1",  # Rewards contract
        "pool": "0x6951bDC4734b9f7F3E1B74afeBC670c736A0EDB6",  # LP token
        "deposit": "0xF403C135812408BFbE8713b5A23a04b3D48AAE31",  # Deposit contract
        "convex_pool_id": 273,
        "convex_url": "https://curve.convexfinance.com/stake/ethereum/273",
        "abis": {
            "pool": "CurveStableSwapNG.json",
            "gauge": "Gauge.json"
        }
    },
    "msETHWETH": {
        "gauge": "0x442E773FFB0043551417D5A37E10c17990fB075c",  # Rewards contract
        "pool": "0xa4c567c662349BeC3D0fB94C4e7f85bA95E208e4",  # LP token
        "deposit": "0xF403C135812408BFbE8713b5A23a04b3D48AAE31",  # Deposit contract
        "convex_pool_id": 217,
        "convex_url": "https://curve.convexfinance.com/stake/ethereum/217",
        "abis": {
            "pool": "Vyper_contract.json",
            "gauge": "Gauge.json"
        }
    }
} 