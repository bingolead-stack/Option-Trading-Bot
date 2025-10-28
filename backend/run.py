"""
Main entry point for the trading bot with FastAPI
"""
import logging
import os
import sys
import threading
import time
from apscheduler.schedulers.background import BackgroundScheduler

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import (
    TASTY_CLIENT_SECRET, TASTY_REFRESH_TOKEN, TASTY_ACCOUNT_NUMBER,
    PAPER_TRADING, SIGNAL_CHECK_INTERVAL, LOG_PATH, LOG_LEVEL, PORT,
    DAYS_TO_EXPIRATION_MIN, DAYS_TO_EXPIRATION_MAX
)
from models.database import DatabaseManager
from bot.tasty_client import TastyClient
from bot.trading_engine import TradingEngine
from api.app import app, set_bot_instance

# Configure logging
os.makedirs(LOG_PATH, exist_ok=True)

# Determine log level
logging.basicConfig(
    level=logging.INFO,  # Use configured log level
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


class TradingBot:
    """Main trading bot orchestrator"""
    
    def __init__(self):
        self.client = None
        self.engine = None
        self.scheduler = None
        self.running = False
        
    def initialize(self):
        """Initialize bot components"""
        try:
            logger.info("Initializing trading bot...")
            
            # Initialize database
            DatabaseManager()
            logger.info("Database initialized")
            
            # Initialize TastyTrade client
            if not TASTY_CLIENT_SECRET or not TASTY_REFRESH_TOKEN:
                logger.warning("TastyTrade OAuth credentials not configured. Running in demo mode.")
                return False
            
            self.client = TastyClient(
                TASTY_CLIENT_SECRET,
                TASTY_REFRESH_TOKEN,
                TASTY_ACCOUNT_NUMBER,
                PAPER_TRADING
            )
            
            # Connect to TastyTrade
            if not self.client.connect():
                logger.error("Failed to connect to TastyTrade")
                return False
            
            # Initialize trading engine
            self.engine = TradingEngine(self.client)
            logger.info("Trading engine initialized")
            logger.info(f"Options DTE Range: {DAYS_TO_EXPIRATION_MIN} to {DAYS_TO_EXPIRATION_MAX} days")
            logger.info(f"Log Level: {LOG_LEVEL}")
            
            # Setup scheduler (runs every 60 seconds to check for signals)
            self.scheduler = BackgroundScheduler()
            self.scheduler.add_job(
                self.engine.run_cycle,
                'interval',
                seconds=SIGNAL_CHECK_INTERVAL,
                id='trading_cycle'
            )
            
            logger.info("Bot initialization complete")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing bot: {e}")
            return False
    
    def start(self):
        """Start the trading bot"""
        if self.running:
            logger.warning("Bot is already running")
            return
        
        try:
            if not self.engine:
                if not self.initialize():
                    logger.error("Cannot start bot - initialization failed")
                    return
            
            self.engine.start()
            self.scheduler.start()
            self.running = True
            
            logger.info("Trading bot started")
            
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
    
    def stop(self):
        """Stop the trading bot"""
        if not self.running:
            logger.warning("Bot is not running")
            return
        
        try:
            if self.engine:
                self.engine.stop()
            
            if self.scheduler:
                self.scheduler.shutdown()
            
            self.running = False
            logger.info("Trading bot stopped")
            
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")
    
    def run(self):
        """Run the bot with FastAPI web interface"""
        logger.info("=" * 60)
        logger.info("OPTIONS TRADING BOT - FastAPI + TastyTrade Integration")
        logger.info("=" * 60)
        logger.info(f"Paper Trading: {PAPER_TRADING}")
        logger.info(f"Account: {TASTY_ACCOUNT_NUMBER}")
        logger.info(f"Framework: FastAPI")
        
        # Set bot instance for API
        set_bot_instance(self)
        
        # Initialize bot (but don't start automatically)
        self.initialize()
        
        # Run FastAPI with Uvicorn
        logger.info("Starting FastAPI server...")
        logger.info(f"API running at: http://localhost:{PORT}")
        logger.info(f"API Docs: http://localhost:{PORT}/api/docs")
        logger.info(f"Dashboard available at: http://localhost:3000")
        
        try:
            import uvicorn
            uvicorn.run(
                app,
                host='0.0.0.0',
                port=PORT,
                log_level='info',
                access_log=False
            )
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            self.stop()


def main():
    """Main entry point"""
    bot = TradingBot()
    bot.run()


if __name__ == '__main__':
    main()
