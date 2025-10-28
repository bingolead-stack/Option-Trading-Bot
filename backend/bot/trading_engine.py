"""
Core trading engine that implements the option premium open breakout strategy
Based on Pine Script: Buys options when price breaks above today's open
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
    """
    Main trading engine implementing option premium open breakout strategy
    
    Strategy:
    1. Find ATM (at-the-money) options at market open (9:30 AM ET)
    2. Record the open price of CALL and PUT options
    3. On 5-minute intervals, check if current price > open price + threshold
    4. If condition met, buy the option (entry signal)
    5. Track positions and P&L
    """
    
    def __init__(self, tasty_client: TastyClient):
        self.client = tasty_client
        self.running = False
        self.open_prices_set = False  # Flag to track if we've set today's open prices
        
    def start(self):
        """Start the trading engine"""
        logger.info("Trading engine started")
        self.running = True
        self.open_prices_set = False
        
    def stop(self):
        """Stop the trading engine"""
        logger.info("Trading engine stopped")
        self.running = False
    
    def is_trading_hours(self) -> bool:
        """Check if currently in trading hours (9:30 AM - 4:00 PM ET)"""
        now = datetime.now().time()
        start = time(TRADING_START_HOUR, TRADING_START_MINUTE)
        end = time(TRADING_END_HOUR, TRADING_END_MINUTE)
        return start <= now <= end
    
    def is_market_open_window(self) -> bool:
        """Check if we're in the market open window (9:30-9:35 AM ET) to set open prices"""
        now = datetime.now().time()
        start = time(TRADING_START_HOUR, TRADING_START_MINUTE)
        end = time(TRADING_START_HOUR, TRADING_START_MINUTE + 5)
        return start <= now <= end
    
    def reset_daily_cache(self):
        """Reset the open prices flag at market open"""
        now = datetime.now()
        current_time = now.time()
        
        # Reset flag before market open (check if it's before 9:30 AM)
        if current_time < time(TRADING_START_HOUR, TRADING_START_MINUTE):
            self.open_prices_set = False
    
    def get_or_set_open_price(self, ticker: str, option_symbol: str, option_type: str, 
                              strike: float, expiration: str, current_price: float, 
                              underlying_price: float) -> float:
        """
        Get or set the open price for an option (recorded at 9:30 AM ET)
        
        Args:
            ticker: Underlying ticker symbol
            option_symbol: Option symbol
            option_type: 'CALL' or 'PUT'
            strike: Strike price
            expiration: Expiration date
            current_price: Current option price
            underlying_price: Current underlying price
            
        Returns:
            The open price for this option
        """
        session = get_session()
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            
            # Check if we already have an open price for today
            cached = session.query(PriceCache).filter_by(
                ticker=ticker,
                option_symbol=option_symbol,
                date=today
            ).first()
            
            if cached and cached.open_price and cached.open_price > 0:
                # Update current price
                cached.current_price = current_price
                cached.underlying_price = underlying_price
                cached.timestamp = datetime.utcnow()
                session.commit()
                return cached.open_price
            
            # Set open price (first time seeing this option today)
            if not cached:
                cached = PriceCache(
                    ticker=ticker,
                    option_symbol=option_symbol,
                    option_type=option_type,
                    strike=strike,
                    expiration=expiration,
                    date=today,
                    open_price=current_price,
                    current_price=current_price,
                    high_price=current_price,
                    low_price=current_price,
                    underlying_price=underlying_price,
                    interval_time=datetime.now().strftime('%H:%M')
                )
                session.add(cached)
                logger.info(f"Set OPEN price for {ticker} {option_type} ${strike}: ${current_price:.2f}")
            else:
                cached.open_price = current_price
                cached.current_price = current_price
                cached.high_price = current_price
                cached.low_price = current_price
                cached.underlying_price = underlying_price
                logger.info(f"Updated OPEN price for {ticker} {option_type} ${strike}: ${current_price:.2f}")
            
            session.commit()
            return current_price
            
        finally:
            session.close()
    
    def check_entry_signal(self, ticker_config: Dict, option_type: str) -> Optional[Dict]:
        """
        Check if entry conditions are met for a ticker option
        
        Strategy: Buy when current_price > open_price * (1 + threshold/100)
        
        Args:
            ticker_config: Ticker configuration from database
            option_type: 'CALL' or 'PUT'
            
        Returns:
            Dictionary with trade details if signal found, None otherwise
        """
        try:
            # Get underlying price
            underlying_price = self.client.get_underlying_price(ticker_config['symbol'])
            if not underlying_price:
                logger.warning(f"Could not get underlying price for {ticker_config['symbol']}")
                return None
            
            # Find ATM option
            option = self.client.find_atm_option(
                ticker_config['symbol'],
                option_type.lower(),
                underlying_price,
                DAYS_TO_EXPIRATION_MIN,
                DAYS_TO_EXPIRATION_MAX
            )
            
            if not option:
                logger.warning(f"Could not find ATM option for {ticker_config['symbol']} {option_type}")
                return None
            
            # Get current option price
            # get_option_quote accepts both OCC and streamer symbols
            quote = self.client.get_option_quote(option['streamer_symbol'])
            if not quote or quote['mark'] <= 0:
                logger.warning(f"Could not get quote for {option['symbol']}")
                return None
            
            current_price = quote['mark']
            
            # Get or set open price
            # Ensure all numeric values are float to avoid Decimal issues
            open_price = self.get_or_set_open_price(
                ticker_config['symbol'],
                option['symbol'],
                option_type,
                float(option['strike']),
                option['expiration'],
                float(current_price),
                float(underlying_price)
            )
            
            if open_price <= 0:
                return None
            
            # Calculate percentage change from open
            # Convert to float to avoid Decimal arithmetic issues
            current_price = float(current_price)
            open_price = float(open_price)
            pct_change = ((current_price - open_price) / open_price) * 100
            
            # Check if threshold met (price must be ABOVE open + threshold)
            threshold = ticker_config['threshold']
            
            logger.debug(
                f"{ticker_config['symbol']} {option_type} ${option['strike']}: "
                f"Open=${open_price:.2f}, Current=${current_price:.2f}, "
                f"Change={pct_change:.2f}%, Threshold={threshold:.2f}%"
            )
            
            if pct_change >= threshold:
                logger.info(
                    f"[ENTRY SIGNAL] {ticker_config['symbol']} {option_type} ${option['strike']} - "
                    f"Open=${open_price:.2f}, Current=${current_price:.2f}, "
                    f"Change={pct_change:.2f}% (Threshold={threshold:.2f}%)"
                )
                
                return {
                    'ticker': ticker_config['symbol'],
                    'option_symbol': option['symbol'],
                    'option_type': option_type,
                    'strike': float(option['strike']),
                    'expiration': option['expiration'],
                    'entry_price': float(current_price),
                    'open_price': float(open_price),
                    'pct_change': float(pct_change),
                    'underlying_price': float(underlying_price)
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking entry signal for {ticker_config['symbol']} {option_type}: {e}")
            return None
    
    def execute_trade(self, signal: Dict, ticker_config: Dict) -> bool:
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
            # Check if we already have an open position for this exact option
            existing = session.query(Trade).filter_by(
                ticker=signal['ticker'],
                option_symbol=signal['option_symbol'],
                status='OPEN'
            ).first()
            
            if existing:
                logger.info(f"Already have open position for {signal['option_symbol']}")
                return False
            
            # Check max positions per ticker
            open_positions = session.query(Trade).filter_by(
                ticker=signal['ticker'],
                status='OPEN'
            ).count()
            
            if open_positions >= ticker_config['max_positions']:
                logger.info(f"Max positions ({ticker_config['max_positions']}) reached for {signal['ticker']}")
                return False
            
            # Calculate quantity (number of contracts)
            # Each contract = 100 shares, cost = entry_price * 100
            cost_per_contract = signal['entry_price'] * 100
            quantity = max(1, int(ticker_config['capital_per_trade'] / cost_per_contract))
            
            # Place order via TastyTrade API
            order_id = self.client.place_order(
                signal['option_symbol'], 
                quantity,
                action='BUY',
                order_type='MARKET'
            )
            
            if not order_id:
                logger.error(f"Failed to place order for {signal['option_symbol']}")
                return False
            
            # Record trade in database
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
                f"[TRADE EXECUTED] {signal['ticker']} {signal['option_type']} "
                f"${signal['strike']} @ ${signal['entry_price']:.2f} x{quantity} contracts "
                f"(Order ID: {order_id})"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            session.rollback()
            return False
        finally:
            session.close()
    
    def process_ticker(self, ticker_symbol: str, ticker_threshold: float, ticker_max_positions: int, ticker_capital_per_trade: float):
        """
        Process a single ticker for trading signals
        
        Args:
            ticker_symbol: Ticker symbol
            ticker_threshold: Price threshold percentage
            ticker_max_positions: Max positions allowed
            ticker_capital_per_trade: Capital allocated per trade
        """
        try:
            # Create a lightweight ticker config dict to avoid session issues
            ticker_config = {
                'symbol': ticker_symbol,
                'threshold': ticker_threshold,
                'max_positions': ticker_max_positions,
                'capital_per_trade': ticker_capital_per_trade
            }
            
            # Check CALL option signal
            call_signal = self.check_entry_signal(ticker_config, 'CALL')
            if call_signal:
                self.execute_trade(call_signal, ticker_config)
            
            # Check PUT option signal
            put_signal = self.check_entry_signal(ticker_config, 'PUT')
            if put_signal:
                self.execute_trade(put_signal, ticker_config)
                
        except Exception as e:
            logger.error(f"Error processing ticker {ticker_symbol}: {e}")
    
    def update_positions(self):
        """Update open positions with current prices and P&L"""
        session = get_session()
        try:
            open_trades = session.query(Trade).filter_by(status='OPEN').all()
            
            if not open_trades:
                return
            
            logger.debug(f"Updating {len(open_trades)} open positions...")
            
            for trade in open_trades:
                try:
                    # Get current quote for the option
                    quote = self.client.get_option_quote(trade.option_symbol)
                    if quote and quote['mark'] > 0:
                        # Update current price
                        trade.exit_price = quote['mark']
                        
                        # Calculate P&L
                        # P&L = (current_price - entry_price) * quantity * 100
                        trade.pnl = (trade.exit_price - trade.entry_price) * trade.quantity * 100
                        
                        logger.debug(
                            f"{trade.ticker} {trade.option_type} ${trade.strike}: "
                            f"Entry=${trade.entry_price:.2f}, Current=${trade.exit_price:.2f}, "
                            f"P&L=${trade.pnl:.2f}"
                        )
                except Exception as e:
                    logger.error(f"Error updating position {trade.option_symbol}: {e}")
                    continue
            
            session.commit()
            
        except Exception as e:
            logger.error(f"Error updating positions: {e}")
        finally:
            session.close()
    
    def run_cycle(self):
        """Run one trading cycle (called every 60 seconds)"""
        if not self.running:
            return
        
        try:
            # Reset cache flag before market open
            self.reset_daily_cache()
            
            # Only trade during market hours
            if not self.is_trading_hours():
                logger.debug("Outside trading hours")
                return
            
            logger.info("=" * 60)
            logger.info(f"Trading cycle at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            session = get_session()
            try:
                # Get all enabled tickers
                tickers = session.query(Ticker).filter_by(enabled=True).all()
                
                if not tickers:
                    logger.warning("No enabled tickers found")
                    return
                
                logger.info(f"Processing {len(tickers)} enabled ticker(s)")
                
                # Process each ticker (extract values to avoid session issues)
                for ticker in tickers:
                    logger.info(f"Checking {ticker.symbol} (threshold: {ticker.threshold}%)...")
                    self.process_ticker(
                        ticker.symbol,
                        ticker.threshold,
                        ticker.max_positions,
                        ticker.capital_per_trade
                    )
                
                # Update existing positions with current prices
                self.update_positions()
                
                logger.info("Trading cycle complete")
                logger.info("=" * 60)
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error in trading cycle: {e}")
