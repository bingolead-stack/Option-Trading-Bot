# Options Trading Bot - TastyTrade Integration

🚀 **Professional Options Trading Bot** with TastyTrade API integration, implementing an **Option Premium Open Breakout Strategy**.

## 📋 Table of Contents

- [Overview](#overview)
- [Strategy Explanation](#strategy-explanation)
- [Features](#features)
- [Technology Stack](#technology-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Trading Strategy Details](#trading-strategy-details)
- [API Documentation](#api-documentation)
- [Troubleshooting](#troubleshooting)
- [Safety & Risk Management](#safety--risk-management)

---

## 🎯 Overview

This trading bot automates options trading on TastyTrade based on a proven **option premium open breakout strategy**. It monitors At-The-Money (ATM) options for specified tickers and executes trades when the option price breaks above the day's opening price by a configurable threshold percentage.

### Key Capabilities

✅ **Fully automated** option trading on TastyTrade  
✅ **Paper trading** mode for risk-free testing  
✅ **Real-time monitoring** of ATM CALL and PUT options  
✅ **Configurable thresholds** per ticker  
✅ **Modern web dashboard** for monitoring and control  
✅ **Position tracking** with live P&L updates  
✅ **Trade history** and performance analytics  

---

## 📊 Strategy Explanation

### The Option Premium Open Breakout Strategy

Based on the provided Pine Script indicator, this bot implements the following logic:

1. **Market Open (9:30 AM ET)**
   - Identifies ATM (At-The-Money) options for each enabled ticker
   - Records the **open price** for both CALL and PUT options at market open

2. **Continuous Monitoring (Every 60 seconds)**
   - Checks current option price against the recorded open price
   - Calculates percentage change: `(current_price - open_price) / open_price * 100`

3. **Entry Signal**
   - **BUY CALL** when: `current_price > open_price * (1 + threshold%)`
   - **BUY PUT** when: `current_price > open_price * (1 + threshold%)`
   - Example: With 0.5% threshold, if CALL opens at $2.00, buy when price hits $2.01+

4. **Position Management**
   - Maximum positions per ticker (default: 2)
   - Capital allocation per trade (default: $500)
   - Automatic P&L tracking

### Why This Strategy Works

- **Momentum-based**: Captures strong moves when option premium expands above open
- **Clear entry rules**: Removes emotional decision-making
- **Both directions**: Trades CALLs and PUTs independently
- **Intraday focus**: Typically uses 0-7 DTE (Days To Expiration) options

---

## ✨ Features

### Trading Features
- ✅ ATM (At-The-Money) option detection
- ✅ Real-time price monitoring via TastyTrade DXFeed
- ✅ Automatic order placement (Market orders)
- ✅ Position tracking with live P&L
- ✅ Per-ticker threshold configuration
- ✅ Maximum position limits
- ✅ Paper trading mode (Certification environment)

### Dashboard Features
- 🎨 Modern dark-themed UI
- 📊 Real-time statistics (P&L, Win Rate, etc.)
- 📈 Live positions table
- 📜 Trade history
- ⚙️ Ticker management (add/remove/enable/disable)
- 🔒 Passkey authentication
- 🟢 Bot start/stop controls

### Technical Features
- ⚡ FastAPI backend with async support
- 🔄 Real-time updates every 60 seconds
- 💾 SQLite database for data persistence
- 📝 Comprehensive logging
- 🛡️ Error handling and recovery
- 📡 RESTful API with Swagger docs

---

## 🛠 Technology Stack

### Backend
- **Python 3.9+**
- **FastAPI** - Modern async web framework
- **SQLAlchemy** - Database ORM
- **TastyTrade SDK** - Official TastyTrade Python library
- **APScheduler** - Task scheduling
- **SQLite** - Embedded database

### Frontend
- **Next.js 14** - React framework
- **TypeScript** - Type-safe JavaScript
- **Tailwind CSS** - Utility-first CSS
- **Axios** - HTTP client
- **Recharts** - Data visualization

---

## 📦 Prerequisites

### Required
1. **Python 3.9 or higher**
2. **Node.js 18+ and npm/yarn**
3. **TastyTrade Account**
   - Sign up at [tastytrade.com](https://tastytrade.com)
   - Get API credentials at [developer.tastytrade.com](https://developer.tastytrade.com)
4. **Git** (for cloning the repository)

### TastyTrade Setup
1. Create a TastyTrade account
2. Enable API access in your account settings
3. Note your username, password, and account number
4. **RECOMMENDED**: Start with paper trading (certification environment)

---

## 🚀 Installation

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd OptionPremiumApp
```

### Step 2: Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Frontend Setup

```bash
# Navigate to frontend directory (from project root)
cd frontend

# Install dependencies
npm install
# or
yarn install
```

### Step 4: Database Initialization

The database will be automatically created on first run. The SQLite database file will be created at:
```
backend/data/trading_bot.db
```

---

## ⚙️ Configuration

### Backend Configuration

1. **Copy the environment template:**
   ```bash
   # From project root
   cp env.template backend/.env
   ```

2. **Edit `backend/.env` with your details:**

```env
# TastyTrade API Configuration
TASTY_USERNAME=your_tastytrade_username
TASTY_PASSWORD=your_tastytrade_password
TASTY_ACCOUNT_NUMBER=your_account_number

# Trading Mode (IMPORTANT: Start with paper trading!)
PAPER_TRADING=true

# Trading Configuration
MAX_POSITIONS_PER_TICKER=2
CAPITAL_PER_TRADE=500
DEFAULT_THRESHOLD=0.5

# Server Configuration
PORT=5000
DEBUG=true
CORS_ORIGINS=http://localhost:3000

# Database Configuration
DATABASE_PATH=backend/data/trading_bot.db

# Logging Configuration
LOG_LEVEL=INFO
LOG_PATH=backend/data/logs

# Risk Management
MAX_DAILY_LOSS=2000
MAX_TOTAL_POSITIONS=10

# Options Selection
DAYS_TO_EXPIRATION_MIN=0
DAYS_TO_EXPIRATION_MAX=7
```

### Frontend Configuration

1. **Create frontend environment file:**
   ```bash
   # From frontend directory
   echo "NEXT_PUBLIC_API_URL=http://localhost:5000" > .env.local
   ```

### Configuration Parameters Explained

| Parameter | Description | Default |
|-----------|-------------|---------|
| `TASTY_USERNAME` | Your TastyTrade username | - |
| `TASTY_PASSWORD` | Your TastyTrade password | - |
| `TASTY_ACCOUNT_NUMBER` | Your account number | - |
| `PAPER_TRADING` | Use paper trading mode | `true` |
| `MAX_POSITIONS_PER_TICKER` | Max open positions per ticker | `2` |
| `CAPITAL_PER_TRADE` | Capital per trade ($) | `500` |
| `DEFAULT_THRESHOLD` | Entry threshold (%) | `0.5` |
| `DAYS_TO_EXPIRATION_MIN` | Min DTE for options | `0` |
| `DAYS_TO_EXPIRATION_MAX` | Max DTE for options | `7` |

---

## 🎮 Usage

### Starting the Bot

#### Terminal 1: Start Backend

```bash
cd backend

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Run the bot
python run.py
```

You should see:
```
============================================================
OPTIONS TRADING BOT - FastAPI + TastyTrade Integration
============================================================
Paper Trading: True
Account: XXXXX
Framework: FastAPI
INFO:     Uvicorn running on http://0.0.0.0:5000
```

#### Terminal 2: Start Frontend

```bash
cd frontend

# Start development server
npm run dev
# or
yarn dev
```

You should see:
```
ready - started server on 0.0.0.0:3000, url: http://localhost:3000
```

### Accessing the Dashboard

1. **Open your browser** and navigate to: `http://localhost:3000`

2. **Login** with default passkey: `admin123`
   - ⚠️ **IMPORTANT**: Change this passkey immediately via Admin Panel

3. **Add Tickers** to monitor:
   - Click "Add Ticker" button
   - Enter ticker symbol (e.g., SPY, QQQ, AAPL)
   - Set threshold percentage (e.g., 0.5 for 0.5%)
   - Click "Add"

4. **Start the Bot**:
   - Click the "Start Bot" button in the header
   - Bot will begin monitoring at market open (9:30 AM ET)

5. **Monitor Activity**:
   - Dashboard updates every 5 seconds
   - View open positions in "Positions" section
   - Check trade history in "Recent Trades" section
   - Monitor P&L in stats cards

### API Documentation

FastAPI provides automatic interactive API documentation:

- **Swagger UI**: `http://localhost:5000/api/docs`
- **ReDoc**: `http://localhost:5000/api/redoc`

---

## 📈 Trading Strategy Details

### How It Works Step-by-Step

#### 1. Pre-Market (Before 9:30 AM ET)
- Bot is idle, waiting for market open
- Clears previous day's cache

#### 2. Market Open (9:30-9:35 AM ET)
- For each enabled ticker:
  - Fetches current underlying price
  - Finds ATM strike (closest to current price)
  - Identifies 0-7 DTE expiration
  - Records CALL and PUT open prices

#### 3. During Trading Hours (9:30 AM - 4:00 PM ET)
- Every 60 seconds, for each ticker:
  - Fetches current option prices
  - Compares to recorded open prices
  - If `(current - open) / open * 100 >= threshold`:
    - Executes BUY order via TastyTrade API
    - Records trade in database
    - Displays in dashboard

#### 4. Position Management
- Updates all open positions every 60 seconds
- Calculates live P&L
- Displays in dashboard

### Example Trade Flow

**Ticker**: SPY  
**Threshold**: 0.5%  
**Capital**: $500  

1. **9:30 AM**: SPY trading at $450
   - ATM Strike: $450
   - CALL open price: $2.00
   - PUT open price: $1.80

2. **10:15 AM**: Market moves up
   - CALL current price: $2.15
   - Change: (2.15 - 2.00) / 2.00 * 100 = **7.5%**
   - **✅ Signal triggered** (7.5% > 0.5% threshold)
   - Bot buys 2 contracts ($2.15 * 100 * 2 = $430)

3. **Real-time Tracking**:
   - Position appears in dashboard
   - P&L updates every 60 seconds
   - Can manually close from UI or let expire

---

## 🔌 API Documentation

### Key Endpoints

#### Bot Control
- `GET /api/bot/status` - Get bot status
- `POST /api/bot/start` - Start the bot
- `POST /api/bot/stop` - Stop the bot

#### Ticker Management
- `GET /api/tickers` - Get all tickers
- `POST /api/tickers` - Add new ticker
- `PUT /api/tickers/{symbol}` - Update ticker
- `DELETE /api/tickers/{symbol}` - Delete ticker
- `PATCH /api/tickers/{symbol}/toggle` - Enable/disable ticker

#### Positions & Trades
- `GET /api/positions` - Get open positions
- `POST /api/positions/{id}/close` - Close position
- `GET /api/trades` - Get trade history
- `GET /api/stats` - Get trading statistics

### Example API Usage

```bash
# Get bot status
curl http://localhost:5000/api/bot/status

# Add a ticker
curl -X POST http://localhost:5000/api/tickers \
  -H "Content-Type: application/json" \
  -d '{"symbol": "SPY", "threshold": 0.5, "enabled": true}'

# Get all positions
curl http://localhost:5000/api/positions
```

---

## 🐛 Troubleshooting

### Common Issues

#### 1. "Failed to connect to TastyTrade"
**Solution:**
- Verify credentials in `.env` file
- Check if API access is enabled in TastyTrade account
- Ensure `PAPER_TRADING=true` for certification environment
- Check internet connection

#### 2. "No enabled tickers found"
**Solution:**
- Add tickers via the dashboard
- Ensure tickers are enabled (toggle switch is ON)
- Check database file exists at `backend/data/trading_bot.db`

#### 3. "Could not find ATM option"
**Solution:**
- Verify ticker has active options
- Check expiration settings (`DAYS_TO_EXPIRATION_MIN/MAX`)
- Ensure market is open
- Try popular tickers like SPY, QQQ first

#### 4. Frontend shows "Network Error"
**Solution:**
- Verify backend is running on port 5000
- Check `CORS_ORIGINS` in backend `.env`
- Verify frontend `.env.local` has correct `NEXT_PUBLIC_API_URL`

#### 5. "Outside trading hours" message
**Solution:**
- Bot only trades 9:30 AM - 4:00 PM ET (Monday-Friday)
- Check your system time is correct
- Note: Bot uses local system time, ensure timezone is correct

### Logs

Check logs for detailed error information:
```bash
# Backend logs
tail -f backend/data/logs/bot.log

# Or check console output
```

---

## 🛡️ Safety & Risk Management

### ⚠️ IMPORTANT SAFETY GUIDELINES

1. **START WITH PAPER TRADING**
   - Always test with `PAPER_TRADING=true` first
   - Paper trade for at least 1-2 weeks
   - Understand all features before going live

2. **Capital Management**
   - Set `CAPITAL_PER_TRADE` conservatively
   - Never risk more than 1-2% of account per trade
   - Use `MAX_POSITIONS_PER_TICKER` to limit exposure

3. **Risk Limits**
   - Configure `MAX_DAILY_LOSS` appropriately
   - Set `MAX_TOTAL_POSITIONS` based on account size
   - Monitor positions regularly

4. **Testing Checklist**
   - ✅ Verify API connection works
   - ✅ Test with 1-2 tickers first
   - ✅ Confirm orders appear in TastyTrade platform
   - ✅ Verify P&L calculations are correct
   - ✅ Test start/stop functionality
   - ✅ Ensure you can manually close positions

5. **Monitoring**
   - Check dashboard multiple times daily
   - Review trade history regularly
   - Monitor system logs for errors
   - Keep TastyTrade platform open for verification

### When to Use Live Trading

Only switch to live trading (`PAPER_TRADING=false`) when:
- ✅ Paper trading works flawlessly for 1-2 weeks
- ✅ You understand the strategy completely
- ✅ You've tested all features
- ✅ Risk limits are properly configured
- ✅ You can actively monitor during market hours

---

## 📝 Project Structure

```
OptionPremiumApp/
├── backend/
│   ├── api/
│   │   └── app.py              # FastAPI application
│   ├── bot/
│   │   ├── tasty_client.py     # TastyTrade API wrapper
│   │   └── trading_engine.py   # Trading logic
│   ├── config/
│   │   └── settings.py         # Configuration
│   ├── models/
│   │   └── database.py         # Database models
│   ├── data/
│   │   ├── trading_bot.db      # SQLite database (created on first run)
│   │   └── logs/               # Log files
│   ├── requirements.txt        # Python dependencies
│   └── run.py                  # Main entry point
├── frontend/
│   ├── app/
│   │   ├── layout.tsx          # Main layout
│   │   ├── page.tsx            # Dashboard page
│   │   └── globals.css         # Global styles
│   ├── components/
│   │   ├── AdminPanel.tsx      # Admin settings
│   │   ├── Header.tsx          # Header component
│   │   ├── LoginScreen.tsx     # Login page
│   │   ├── Positions.tsx       # Positions table
│   │   ├── StatsCards.tsx      # Statistics cards
│   │   ├── TickerManagement.tsx # Ticker controls
│   │   └── TradeHistory.tsx    # Trade history
│   ├── lib/
│   │   ├── api.ts              # API client
│   │   └── auth.ts             # Authentication
│   ├── package.json            # Node dependencies
│   └── next.config.js          # Next.js config
├── env.template                # Environment template
└── README.md                   # This file
```

---

## 🤝 Support

### Getting Help

1. **Check logs**: `backend/data/logs/bot.log`
2. **API docs**: `http://localhost:5000/api/docs`
3. **TastyTrade API docs**: [developer.tastytrade.com](https://developer.tastytrade.com)

---

## 📜 License

This project is for educational and personal use. Always comply with TastyTrade's API terms of service and your local regulations regarding automated trading.

---

## ⚡ Quick Start Summary

```bash
# 1. Setup backend
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp ../env.template .env
# Edit .env with your TastyTrade credentials

# 2. Setup frontend
cd ../frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:5000" > .env.local

# 3. Run (in separate terminals)
# Terminal 1:
cd backend
python run.py

# Terminal 2:
cd frontend
npm run dev

# 4. Open browser
# http://localhost:3000
# Login with: admin123 (change immediately!)
```

---

**Happy Trading! 🚀📈**

*Remember: Past performance is not indicative of future results. Always start with paper trading and understand the risks.*

