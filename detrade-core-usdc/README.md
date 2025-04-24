# DeTrade Core USDC

A Python-based system for tracking and aggregating DeFi positions across multiple protocols and networks, with a focus on USDC valuation.

Developed by [AP3Labs](https://ap3labs.com) for [DeTrade](https://detrade.fund).

Live implementation can be found at [oracle.detrade.fund](https://oracle.detrade.fund).

## Configuration

Copy `.env.example` to `.env` and configure your environment variables:
- RPC endpoints (Ethereum, Base)
- MongoDB connection

### Addresses
- Production: `0xc6835323372A4393B90bCc227c58e82D45CE4b7d`
- Testing: `0xAbD81C60a18A34567151eA70374eA9c839a41cF5`

## Overview

DeTrade Core USDC is a comprehensive portfolio tracking system that:
- Aggregates positions across multiple DeFi protocols (Pendle, Convex, Sky Protocol, Equilibria, Tokemak)
- Tracks spot positions (USDC, ETH, etc.) across networks
- Tracks positions across different networks (Ethereum, Base)
- Converts all positions to USDC value using various price discovery mechanisms
- Stores historical portfolio data in MongoDB
- Calculates share price based on total value and supply

## System Architecture

### Network Configuration (`config/networks.py`)

The networks.py file serves as the central configuration hub for all supported networks and tokens. It defines:

1. **RPC Endpoints**: Connection points for each supported blockchain network
2. **Chain IDs**: Network identifiers for transaction handling
3. **Token Registry**: Comprehensive token configurations organized by network and type:
   - Yield-bearing tokens (e.g., Pendle PTs, Tokemak positions)
   - Base stablecoins (USDC, USDS, etc.)
   - Protocol tokens (PENDLE, TOKE, etc.)

Each token entry includes essential metadata:
- Contract address
- Decimals
- Protocol information (for yield-bearing tokens)
- Market addresses (for protocol-specific interactions)
- Underlying asset information

This centralized configuration enables:
- Easy addition of new networks and tokens
- Consistent token handling across the system
- Protocol-specific balance tracking
- Price discovery and conversion logic

### Price Discovery Service (`cowswap/cow_client.py`)

The system uses CoW Protocol for accurate price discovery and token valuations. The CoW client:

- Provides reliable price quotes for converting any token to USDC
- Implements smart fallback mechanisms for small amounts
- Handles multiple networks (Ethereum, Base)

Key features:
- Direct price quotes from CoW Protocol API
- Fallback price discovery using reference amounts
- Automatic retry mechanism with delays
- Detailed conversion tracking including:
  - Price impact
  - Exchange rates
  - Fee calculations
  - Conversion method used

### Protocol-Specific Balance Managers

The system implements different balance managers optimized for each protocol's architecture:

#### Pendle & Equilibria (`pendle/`, `equilibria/`)
- Hybrid approach combining on-chain data and Pendle SDK
- Direct market queries for accurate PT (Principal Token) pricing
- Specialized handling for expired/matured positions
- Fallback to underlying asset pricing when needed

#### Convex, Tokemak & Sky Protocol
- Primarily on-chain balance and reward tracking
- CoW Protocol integration for token-to-USDC conversion
- Direct smart contract interactions for position data
- Optimized for gas efficiency and reliability

#### Spot Positions
- Simple `balanceOf` queries for token balances
- Direct CoW Protocol conversion to USDC
- Leverages token configurations from `networks.py`
- Handles both native tokens and ERC20s

Each balance manager:
- Implements standardized interfaces for system integration
- Provides detailed conversion tracking and audit trails
- Handles protocol-specific edge cases and failure modes
- Contributes to the global USDC portfolio valuation

### Code Documentation & Logging

The system features extensive in-code documentation and logging:

- Detailed docstrings explaining methodology and edge cases
- Comprehensive logging of each conversion step
- Real-time price impact and rate monitoring
- Clear error handling and fallback explanations

Example log output shows:
- Contract interactions and function calls
- Balance fetching and normalization
- Price discovery methodology
- Conversion rates and impacts
- Fallback mechanism activation
- Final USDC valuations

This logging system helps:
- Debug conversion issues
- Monitor price discovery accuracy
- Track protocol-specific behaviors
- Audit final portfolio valuations

## Testing & Production Addresses

The system uses two main addresses for portfolio tracking:

- `TESTING_USER_ADDRESS`: Points to a Safe associated with the "dev DeTrade Core USDC" vault in production, used for testing purposes
- `DEFAULT_USER_ADDRESS`: Points to the current production Safe where the strategy is actively running

These addresses are configurable in the `.env` file (see `.env.example`) and are crucial for the system to function properly as they determine which portfolio positions are tracked.

## Builder Module

The builder module is the core component responsible for aggregating and processing portfolio data. It consists of two main components:

### 1. Aggregator (`builder/aggregator.py`)

The aggregator is responsible for:

- Fetching balances from multiple protocols
- Converting all positions to USDC value
- Building a standardized portfolio overview

Key features:
- Protocol-specific balance managers for accurate position tracking
- Price discovery through multiple sources (Pendle SDK, CoWSwap, direct conversions)
- Fallback mechanisms for handling small amounts
- Detailed conversion tracking with price impact and rates

### 2. Pusher (`builder/pusher.py`)

The pusher handles:
- Data validation and formatting
- MongoDB storage operations
- Historical data management
- Share price calculations

## Installation & Setup

1. Clone the repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure environment variables:
   - Copy `.env.example` to `.env`
   - Update the values in `.env` with your configuration

## Data Structure

### MongoDB Collections

The system stores portfolio data in MongoDB with the following structure:

```json
{
    "nav": {
        "usdc": "336967.110883",  // Total portfolio value in USDC
        "share_price": "1.010997", // Current DTUSDC share price
        "total_supply": "333301.829440" // Total DTUSDC supply
    },
    "overview": {
        "summary": {
            "total_value_usdc": "336967.110883",
            "protocols_value_usdc": "336952.886209",
            "spot_value_usdc": "14.224674"
        },
        "positions": {
            "pendle.base.PT-USR-24APR2025": "99715.120834",
            "pendle.ethereum.PT-eUSDE-29MAY2025": "87140.775354",
            "pendle.ethereum.PT-cUSDO-19JUN2025": "82269.452139",
            "convex.ethereum.USDCfxUSD": "61248.910571",
            "sky.base.sUSDS": "6578.627311"
        }
    },
    "protocols": {
        "pendle": {
            "ethereum": {
                "PT-eUSDE-29MAY2025": {
                    "amount": "87910927839117593803460",
                    "decimals": 18,
                    "value": {
                        "USDC": {
                            "amount": "87140775354",
                            "decimals": 6,
                            "conversion_details": {
                                "source": "Pendle SDK",
                                "price_impact": "-0.000163",
                                "rate": "0.991239",
                                "fee_percentage": "0.0000%",
                                "fallback": false,
                                "note": "Direct Conversion using Pendle SDK"
                            }
                        }
                    }
                }
            },
            "usdc_totals": {
                "total": {
                    "wei": 269125348327,
                    "formatted": "269125.348327"
                }
            }
        },
        "convex": {
            "ethereum": {
                "USDCfxUSD": {
                    "lp_tokens": {
                        // LP token positions
                    },
                    "rewards": {
                        // Reward token positions
                    }
                }
            }
        },
        "sky": {
            "base": {
                // Sky Protocol positions
            }
        }
    },
    "spot": {
        "ethereum": {
            "CVX": {
                "amount": "42286323783015506",
                "decimals": 18,
                "value": {
                    "USDC": {
                        "amount": "116983",
                        "decimals": 6,
                        "conversion_details": {
                            "source": "CoWSwap-Fallback",
                            "price_impact": "N/A",
                            "rate": "2.766459",
                            "fee_percentage": "N/A",
                            "fallback": true,
                            "note": "Using reference amount of 1000 tokens for price discovery"
                        }
                    }
                }
            }
        }
    },
    "address": "0xc6835323372A4393B90bCc227c58e82D45CE4b7d",
    "created_at": "2025-04-24 06:40:30 UTC"
}
```

Key sections:
- `nav`: Overall portfolio metrics including share price
- `overview`: Quick summary of total values positions
- `protocols`: Detailed breakdown of protocol-specific positions
- `spot`: Direct token holdings across networks

Each position includes:
- Raw amount and decimals
- USDC value with conversion details
- Price impact and conversion rates
- Source of price data
- Any fallback mechanisms used

The system maintains detailed conversion tracking for audit purposes and includes comprehensive logging in the code for debugging and monitoring.
