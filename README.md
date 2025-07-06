# Oracle DeTrade Fund WETH

A comprehensive blockchain oracle system for real-time portfolio valuation and financial data aggregation across multiple DeFi protocols.

## 🏗️ Architecture Overview

This system provides automated, real-time portfolio tracking and valuation by directly sourcing data from blockchain smart contracts and aggregating pricing information through decentralized exchanges.

### Core Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Blockchain    │────│   Price Oracle  │────│   Data Storage  │
│   Data Source   │    │   Aggregator    │    │    MongoDB      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
    ┌────▼────┐              ┌───▼───┐              ┌────▼────┐
    │Protocol │              │CoWSwap│              │Snapshot │
    │Managers │              │Pricing│              │Builder  │
    └─────────┘              └───────┘              └─────────┘
```

## 📊 Supported Protocols

### **Pendle Finance**
- **PT Token Positions**: Principal Token balances across markets
- **LP Token Positions**: Liquidity provider token holdings
- **Networks**: Ethereum, Base
- **Features**: Automatic conversion quotes, market data refresh

### **Curve Finance**
- **Pool Positions**: cbETH-f pool on Base network
- **Rewards Tracking**: Unclaimed reward tokens
- **Features**: Pool share calculation, reward valuation

### **Convex Finance** 
- **Staked Positions**: WETH/tacETH pool on Ethereum
- **Reward Tracking**: CRV and other reward tokens
- **Features**: LP token valuation, compound reward calculation

### **Spot Holdings**
- **Native Tokens**: ETH, WETH balances
- **ERC20 Tokens**: USDC and other standard tokens
- **Networks**: Ethereum, Base

## 🔄 Price Aggregation System

### CoWSwap Integration
The system uses CoW Protocol for decentralized price discovery:

```python
# Example: Converting PT tokens to WETH
quote = get_quote(
    network="ethereum",
    sell_token=pt_token_address,
    buy_token=weth_address,
    amount=token_balance,
    token_decimals=18
)
```

### Multi-Step Conversion Process
1. **Direct Conversion**: Native WETH holdings (1:1 ratio)
2. **Protocol Conversion**: PT/LP tokens → Underlying assets
3. **Price Discovery**: Underlying assets → WETH via CoWSwap
4. **Aggregation**: Sum all WETH-equivalent values

## 📸 Snapshot Generation

### Data Collection Flow
```
Smart Contracts → Balance Readers → Protocol Managers → Aggregator → MongoDB
```

### Snapshot Structure
```json
{
  "nav": {
    "weth": "123.456789",
    "share_price": "1.234567",
    "total_supply": "100.000000"
  },
  "positions": {
    "pendle.ethereum.PT-stETH-26DEC2024": "45.123456",
    "curve.base.cbeth-f": "32.789012",
    "convex.ethereum.WETH/tacETH": "28.456789",
    "spot.ethereum": "17.891234"
  },
  "protocols": { /* Detailed breakdown */ },
  "spot": { /* Token-by-token breakdown */ },
  "address": "0x...",
  "created_at": "2024-01-15 10:30:45 UTC"
}
```

## 🏦 Share Price Calculation

### dtWETH Token Integration
The system integrates with dtWETH smart contracts to calculate accurate share prices:

```python
# Read total supply from dtWETH contract
supply_reader = SupplyReader(address=wallet_address)
total_supply = supply_reader.format_total_supply()

# Calculate share price
share_price = total_nav_value / total_supply
```

### Key Metrics
- **Total NAV**: Sum of all positions valued in WETH
- **Share Price**: NAV per dtWETH token
- **Total Supply**: Current dtWETH token circulation

## 🗄️ Data Storage & MongoDB Integration

### Automated Data Pipeline
```python
# Push data to MongoDB
pusher = BalancePusher(
    database_name="detrade-core-eth",
    collection_name="oracle"
)
pusher.push_balance_data(wallet_address)
```

### Database Configuration
- **Production DB**: `detrade-core-eth`
- **Development DB**: `dev-detrade-core-eth`
- **Collection**: `oracle`
- **Retention**: Configurable document lifecycle

## 🚀 Automation & GitHub Actions

### Manual Trigger Support
The system supports external triggering through GitHub Actions for third-party application integration:

```yaml
# Example GitHub Action trigger
name: Oracle Update
on:
  workflow_dispatch:
    inputs:
      target_address:
        description: 'Wallet address to process'
        required: true
        default: '0x66DbceE7feA3287B3356227d6F3DfF3CeFbC6F3C'
```

### External API Integration
Third-party applications can trigger oracle updates via:
- GitHub API workflow dispatch
- Webhook endpoints
- Scheduled automation

## 🛠️ Getting Started

### Prerequisites
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration
```

### Environment Configuration
```env
# RPC Endpoints
ETHEREUM_RPC=https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY
BASE_RPC=https://base-mainnet.g.alchemy.com/v2/YOUR_KEY

# Database
MONGO_URI=mongodb://localhost:27017
DATABASE_NAME=detrade-core-eth
COLLECTION_NAME=oracle

# Wallet
PRODUCTION_ADDRESS=0x66DbceE7feA3287B3356227d6F3DfF3CeFbC6F3C
```

### Basic Usage

#### Run Complete Oracle Update
```bash
# Full pipeline execution
python -m builder.aggregator 0x66DbceE7feA3287B3356227d6F3DfF3CeFbC6F3C

# Push to MongoDB
python -m builder.pusher
```

#### Individual Protocol Queries
```bash
# Pendle positions only
python -m pendle.pendle_manager

# Curve positions only  
python -m curve.curve_manager

# Spot balances only
python -m spot.balance_manager
```

#### Database Operations
```bash
# Check latest entries
python -m mongo.check_mongo

# Clean old data
python -m mongo.delete_documents_after_date detrade-core-eth "2024-01-01 00:00:00 UTC"
```

## 🔧 Technical Features

### Retry Logic & Error Handling
- **Web3 Retry**: Automatic retry for blockchain calls
- **API Retry**: Robust handling of external API failures
- **Fallback Pricing**: Multiple pricing sources for reliability

### Performance Optimizations
- **Parallel Processing**: Concurrent protocol data fetching
- **Caching**: Market data caching for efficiency
- **Rate Limiting**: Respectful API usage patterns

### Security Features
- **Address Validation**: Checksum address verification
- **Input Sanitization**: Safe parameter handling
- **Error Isolation**: Protocol failures don't crash entire pipeline

## 📈 Monitoring & Observability

### Logging System
```python
# Structured logging throughout
logger.info("✓ Pendle positions fetched successfully")
logger.error("✗ Error fetching Curve positions: {error}")
```

### Data Validation
- **Balance Verification**: Cross-reference blockchain data
- **Price Sanity Checks**: Detect and handle price anomalies
- **Completeness Validation**: Ensure all protocols processed