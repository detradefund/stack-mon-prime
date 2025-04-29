# DeTrade Core USDC Oracle

A decentralized price oracle service that aggregates and values DeFi positions across multiple protocols to calculate the Net Asset Value (NAV) of DeTrade Core USDC (DTUSDC).

## Overview

The oracle tracks positions across various DeFi protocols and provides:
- Real-time position valuation in USDC
- Aggregated portfolio NAV calculation
- DTUSDC share price computation
- Historical data storage via MongoDB

## Architecture

### Core Components

#### Config Layer (`/config`)
- **Network Configuration** (`networks.py`):
  - RPC endpoints per chain
  - Token registry and mappings
  - Protocol configurations
- **Base Client** (`base_client.py`):
  - Abstract protocol interface
  - Standardized data structures

#### Protocol Layer
- **Balance Managers**:
  - Smart contract interactions
  - Balance fetching
  - Protocol-specific conversion
  - Error handling
- **CoW Protocol Integration**:
  - Centralized price discovery
  - Market-based conversion
  - Fallback mechanisms
  - Standardized quoting

#### Builder Layer (`/builder`)
- **Aggregator** (`aggregator.py`):
  - Protocol orchestration
  - Position aggregation
  - NAV calculation
- **Pusher** (`pusher.py`):
  - MongoDB integration
  - Data validation
  - Performance tracking

### Web Interface (`/src`)
- **Frontend Stack**:
  - SvelteKit + TypeScript
  - Real-time updates
  - Historical data view
- **Key Components**:
  - OracleBox: Position display
  - InfoBox: System overview
  - Responsive design

### Deployment
- **Infrastructure**:
  - Frontend: Vercel ([oracle.detrade.fund](https://oracle.detrade.fund))
  - Database: MongoDB Atlas
  - Automation: GitHub Actions
- **Update Process**:
  - 30-minute cron job
  - Position fetching
  - Value calculation
  - Database storage
  - Frontend update

## Protocol Integrations

### Direct USDC Protocols

#### Tokemak
- **Integration Type**: Single-sided USDC staking
- **Components**:
  - autoUSD pool token
  - MainRewarder contract
- **Process Flow**:
  1. Balance Fetching:
     - Staked USDC from MainRewarder
     - Earned TOKE rewards
  2. Value Calculation:
     - Direct 1:1 USDC conversion
     - TOKE rewards via CoW Protocol

### Curve-Based Protocols

#### Convex Finance
- **Integration Type**: Curve LP + Rewards
- **Components**:
  - Dedicated vault system
  - USDC-fxUSD Curve pool
  - Gauge and reward contracts
- **Process Flow**:
  1. Position Discovery:
     - Vault whitelist check
     - LP token balance from gauge
  2. Value Calculation:
     - Pool share calculation
     - USDC portion: Direct 1:1
     - fxUSD portion: CoW Protocol quote
     - CRV/CVX rewards conversion

### Pendle Integrations

#### Pendle Finance
- **Integration Type**: Principal Tokens (PT)
- **Supported Markets**:
  - PT-eUSDE-29MAY2025 (ETH)
  - PT-cUSDO-19JUN2025 (ETH)
  - PT-USR-24APR2025 (Base)
- **Process Flow**:
  1. Balance Fetching:
     - Direct PT balance check
     - Cross-chain support
  2. Value Calculation:
     - Pendle SDK price discovery
     - Direct PT -> USDC conversion

#### Equilibria
- **Integration Type**: Pendle Boosted LP
- **Components**:
  - GHO-USR LP via Pendle Booster
  - BaseRewardPool contract
- **Process Flow**:
  1. Position Tracking:
     - Staked LP from BaseRewardPool
     - PENDLE/CRV rewards
  2. Value Calculation:
     - Pendle SDK for LP removal quote
     - CoW Protocol for rewards

### Savings Protocols

#### Sky Protocol
- **Integration Type**: Yield-bearing USDS
- **Deployment**:
  - Ethereum: 0xa3931d71...
  - Base: 0x5875eEE11...
- **Process Flow**:
  1. Balance Tracking:
     - sUSDS balance check
     - Cross-chain aggregation
  2. Value Calculation:
     - sUSDS -> USDS conversion
     - USDS -> USDC via CoW Protocol

## Installation & Setup

### Requirements
- Python 3.10+
- MongoDB instance
- Node.js 18+ (for frontend)

### Backend Setup
1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables:
```bash
# MongoDB configuration
MONGO_URI=your_mongodb_uri

# Network RPC endpoints
ETH_RPC_URL=your_ethereum_rpc
BASE_RPC_URL=your_base_rpc
```

3. Database Configuration:
The system uses two hardcoded databases:
- `detrade-core-usdc`: Production database
- `dev-detrade-core-usdc`: Development database

The addresses and database configurations are hardcoded in `builder/pusher.py`:
```python
configurations = [
    {
        'address': '0xc6835323372A4393B90bCc227c58e82D45CE4b7d',  # Production address
        'database_name': 'detrade-core-usdc',
        'collection_name': 'oracle'
    },
    {
        'address': '0xAbD81C60a18A34567151eA70374eA9c839a41cF5',  # Development address
        'database_name': 'dev-detrade-core-usdc',
        'collection_name': 'oracle'
    }
]
```

4. Verify protocol modules:
```bash
# Test individual protocols
python -m pendle.balance_manager
python -m convex.balance_manager
python -m sky.balance_manager
python -m tokemak.balance_manager
python -m equilibria.balance_manager

# Test aggregation
python -m builder.aggregator

# Test database pushing
python -m builder.pusher
```

### Frontend Setup
1. Install Node.js dependencies:
```bash
npm install
```

2. Configure environment:
```bash
# .env
PUBLIC_MONGODB_URI=your_mongodb_uri
```

3. Run development server:
```bash
npm run dev
```

### Deployment
1. Set up GitHub Actions workflow
2. Configure Vercel project
3. Set up MongoDB Atlas connection
4. Deploy frontend to Vercel
5. Verify cron job execution

