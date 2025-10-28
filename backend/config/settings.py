"""
Configuration settings for the trading bot
"""
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# TastyTrade API Configuration (OAuth)
TASTY_CLIENT_SECRET = os.getenv('TASTY_CLIENT_SECRET', '')
TASTY_REFRESH_TOKEN = os.getenv('TASTY_REFRESH_TOKEN', '')
TASTY_ACCOUNT_NUMBER = os.getenv('TASTY_ACCOUNT_NUMBER', '')

# Trading Configuration
PAPER_TRADING = os.getenv('PAPER_TRADING', 'true').lower() == 'true'
MAX_POSITIONS_PER_TICKER = int(os.getenv('MAX_POSITIONS_PER_TICKER', 2))
CAPITAL_PER_TRADE = float(os.getenv('CAPITAL_PER_TRADE', 500))
DEFAULT_THRESHOLD = float(os.getenv('DEFAULT_THRESHOLD', 0.5))

# Server Configuration
PORT = int(os.getenv('PORT', 5000))
DEBUG = os.getenv('DEBUG', 'true').lower() == 'true'
CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')

# Database Configuration
DATABASE_PATH = os.path.join(BASE_DIR, os.getenv('DATABASE_PATH', 'data/trading_bot.db'))

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG')
LOG_PATH = os.path.join(BASE_DIR, os.getenv('LOG_PATH', 'data/logs'))

# Trading Hours (Eastern Time)
TRADING_START_HOUR = 9
TRADING_START_MINUTE = 30
TRADING_END_HOUR = 16
TRADING_END_MINUTE = 0

# Data Update Intervals (seconds)
PRICE_UPDATE_INTERVAL = 300  # 5 minutes (300 seconds) for 5-min candles
POSITION_UPDATE_INTERVAL = 60  # Check positions every 60 seconds
SIGNAL_CHECK_INTERVAL = 60  # Check for signals every 60 seconds

# Risk Management
MAX_DAILY_LOSS = 2000  # Maximum loss per day in dollars
MAX_TOTAL_POSITIONS = 10  # Maximum total open positions

# Options Selection
DAYS_TO_EXPIRATION_MIN = 0  # 0 DTE (same day)
DAYS_TO_EXPIRATION_MAX = 7  # Up to 7 days out

