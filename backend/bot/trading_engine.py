"""
Core trading engine that implements the strategy
"""
import logging
from datetime import datetime, time
from typing import Dict, Optional
from models.database import get_session, Ticker, Trade, PriceCache, BotStatus
from bot.tasty_client import TastyClient
from config.settings import (
    TRADING_START_HOUR, TRADING_START_MINUTE,
    TRADING_END_HOUR, TRADING_END_MINUTE,
    MAX_POSITIONS_PER_TICKER, DAYS_TO_EXPIRATION_MIN, 
    DAYS_TO_EXPIRATION_MAX
)

logger = logging.getLogger(__name__)


class TradingEngine:
    """Main trading engine"""
    
    def __init__(self, tasty_client: TastyClient):
        self.client = tasty_client
        self.running = False
        self.open_prices_cache = {}  # {ticker: {option_symbol: open_price}}
        
    def start(self):
        """Start the trading engine"""
        logger.info("Trading engine started")
        self.running = True
        
    def stop(self):
        """Stop the trading engine"""
        logger.info("Trading engine stopped")
        self.running = False
    
    def is_trading_hours(self) -> bool:
        """Check if currently in trading hours"""
        now = datetime.now().time()
        start = time(TRADING_START_HOUR, TRADING_START_MINUTE)
        end = time(TRADING_END_HOUR, TRADING_END_MINUTE)
        return start <= now <= end
    
    def get_open_price(self, ticker: str, option_symbol: str, current_price: float) -> float:
        """
        Get or set the open price for an option
        
        Args:
            ticker: Underlying ticker symbol
            option_symbol: Option symbol
            current_price: Current price of the option
            
        Returns:
            The open price for this option
        """
        session = get_session()
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            
            # Check cache first
            cache_key = f"{ticker}_{option_symbol}_{today}"
            if cache_key in self.open_prices_cache:
                return self.open_prices_cache[cache_key]
            
            # Check database
            cached = session.query(PriceCache).filter_by(
                ticker=ticker,
                option_symbol=option_symbol,
                date=today
            ).first()
            
            if cached and cached.open_price:
                self.open_prices_cache[cache_key] = cached.open_price
                return cached.open_price
            
            # Set current price as open price (first time seeing this option today)
            if not cached:
                cached = PriceCache(
                    ticker=ticker,
                    option_symbol=option_symbol,
                    option_type='',  # Will be set by caller
                    strike=0,
                    expiration='',
                    date=today,
                    open_price=current_price,
                    current_price=current_price
                )
                session.add(cached)
            else:
                cached.open_price = current_price
                
            session.commit()
            self.open_prices_cache[cache_key] = current_price
            
            logger.info(f"Set open price for {option_symbol}: ${current_price:.2f}")
            return current_price
            
        finally:
            session.close()
    
    def check_entry_signal(self, ticker_config: Ticker, option_type: str) -> Optional[Dict]:
        """
        Check if entry conditions are met for a ticker
        
        Args:
            ticker_config: Ticker configuration from database
            option_type: 'CALL' or 'PUT'
            
        Returns:
            Dictionary with trade details if signal found, None otherwise
        """
        try:
            # Get underlying price
            underlying_price = self.client.get_underlying_price(ticker_config.symbol)
            if not underlying_price:
                return None
            
            # Find ATM option
            option = self.client.find_atm_option(
                ticker_config.symbol,
                option_type,
                underlying_price,
                DAYS_TO_EXPIRATION_MIN,
                DAYS_TO_EXPIRATION_MAX
            )
            
            if not option:
                return None
            
            # Get current option price
            quote = self.client.get_option_quote(option['symbol'])
            if not quote or quote['mark'] <= 0:
                return None
            
            current_price = quote['mark']
            
            # Get open price (or set it if first time today)
            open_price = self.get_open_price(
                ticker_config.symbol,
                option['symbol'],
                current_price
            )
            
            # Calculate percentage change
            if open_price <= 0:
                return None
                
            pct_change = ((current_price - open_price) / open_price) * 100
            
            # Check if threshold met
            threshold = ticker_config.threshold
            if pct_change >= threshold:
                logger.info(
                    f"Entry signal for {ticker_config.symbol} {option_type}: "
                    f"Open=${open_price:.2f}, Current=${current_price:.2f}, "
                    f"Change={pct_change:.2f}%, Threshold={threshold:.2f}%"
                )
                
                return {
                    'ticker': ticker_config.symbol,
                    'option_symbol': option['symbol'],
                    'option_type': option_type,
                    'strike': option['strike'],
                    'expiration': option['expiration'],
                    'entry_price': current_price,
                    'open_price': open_price,
                    'pct_change': pct_change,
                    'underlying_price': underlying_price
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking entry signal for {ticker_config.symbol}: {e}")
            return None
    
    def execute_trade(self, signal: Dict, ticker_config: Ticker) -> bool:
        """
        Execute a trade based on signal
        
        Args:
            signal: Trade signal dictionary
            ticker_config: Ticker configuration
            
        Returns:
            True if trade executed successfully
        """
        session = get_session()
        try:
            # Check if we have room for more positions
            open_positions = session.query(Trade).filter_by(
                ticker=signal['ticker'],
                status='OPEN'
            ).count()
            
            if open_positions >= ticker_config.max_positions:
                logger.info(f"Max positions reached for {signal['ticker']}")
                return False
            
            # Calculate quantity (number of contracts)
            quantity = max(1, int(ticker_config.capital_per_trade / (signal['entry_price'] * 100)))
            
            # Place order
            order_id = self.client.place_order(signal['option_symbol'], quantity)
            
            if not order_id:
                logger.error(f"Failed to place order for {signal['option_symbol']}")
                return False
            
            # Record trade
            trade = Trade(
                ticker=signal['ticker'],
                option_type=signal['option_type'],
                option_symbol=signal['option_symbol'],
                strike=signal['strike'],
                expiration=signal['expiration'],
                entry_price=signal['entry_price'],
                quantity=quantity,
                status='OPEN',
                open_price_ref=signal['open_price'],
                order_id=order_id,
                entry_time=datetime.utcnow()
            )
            
            session.add(trade)
            session.commit()
            
            logger.info(
                f"Trade executed: {signal['ticker']} {signal['option_type']} "
                f"{signal['strike']} @ ${signal['entry_price']:.2f} x{quantity}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            session.rollback()
            return False
        finally:
            session.close()
    
    def process_ticker(self, ticker_config: Ticker):
        """
        Process a single ticker for trading signals
        
        Args:
            ticker_config: Ticker configuration from database
        """
        if not ticker_config.enabled:
            return
        
        # Check CALL signal
        call_signal = self.check_entry_signal(ticker_config, 'CALL')
        if call_signal:
            self.execute_trade(call_signal, ticker_config)
        
        # Check PUT signal
        put_signal = self.check_entry_signal(ticker_config, 'PUT')
        if put_signal:
            self.execute_trade(put_signal, ticker_config)
    
    def update_positions(self):
        """Update open positions with current prices"""
        session = get_session()
        try:
            open_trades = session.query(Trade).filter_by(status='OPEN').all()
            
            for trade in open_trades:
                # Get current quote
                quote = self.client.get_option_quote(trade.option_symbol)
                if quote:
                    # Update with current mark price
                    trade.exit_price = quote['mark']
                    
                    # Calculate P&L
                    trade.pnl = (trade.exit_price - trade.entry_price) * trade.quantity * 100
            
            session.commit()
            
        except Exception as e:
            logger.error(f"Error updating positions: {e}")
        finally:
            session.close()
    
    def run_cycle(self):
        """Run one trading cycle"""
        if not self.running:
            return
        
        if not self.is_trading_hours():
            logger.debug("Outside trading hours")
            return
        
        session = get_session()
        try:
            # Get all enabled tickers
            tickers = session.query(Ticker).filter_by(enabled=True).all()
            
            logger.info(f"Processing {len(tickers)} tickers")
            
            for ticker in tickers:
                self.process_ticker(ticker)
            
            # Update existing positions
            self.update_positions()
            
        finally:
            session.close()

