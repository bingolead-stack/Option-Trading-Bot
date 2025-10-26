"""
TastyTrade API Client Wrapper
Handles connection to TastyTrade API and option trading operations
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from tastytrade import Session, Account
from tastytrade.dxfeed import EventType
from tastytrade.instruments import get_option_chain, NestedOptionChain
from tastytrade.order import NewOrder, OrderAction, OrderTimeInForce, OrderType, PriceEffect, OrderStatus
import time

logger = logging.getLogger(__name__)


class TastyClient:
    """Wrapper for TastyTrade API"""
    
    def __init__(self, username: str, password: str, account_number: str, paper_trading: bool = True):
        self.username = username
        self.password = password
        self.account_number = account_number
        self.paper_trading = paper_trading
        self.session = None
        self.account = None
        
    def connect(self) -> bool:
        """Connect to TastyTrade API"""
        try:
            # Create session with appropriate environment
            # In tastytrade 8.2+, Session handles both production and certification
            # Use is_test parameter to specify environment
            self.session = Session(
                self.username, 
                self.password,
                is_test=self.paper_trading  # True for paper trading, False for live
            )
            
            if self.paper_trading:
                logger.info("Connected to TastyTrade Certification (Paper) environment")
            else:
                logger.info("Connected to TastyTrade Production environment")
            
            # Get account
            accounts = Account.get_accounts(self.session)
            
            if not accounts:
                logger.error("No accounts found")
                return False
            
            # If account number specified, find it; otherwise use first account
            if self.account_number:
                self.account = next(
                    (a for a in accounts if a.account_number == self.account_number), 
                    None
                )
                if not self.account:
                    logger.error(f"Account {self.account_number} not found")
                    logger.info(f"Available accounts: {[a.account_number for a in accounts]}")
                    return False
            else:
                # Use first account if no account number specified
                self.account = accounts[0]
                logger.info(f"No account number specified, using first account: {self.account.account_number}")
            
            logger.info(f"Account loaded: {self.account.account_number}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to TastyTrade: {e}")
            logger.error(f"Error details: {type(e).__name__}: {str(e)}")
            return False
    
    def get_option_chain(self, symbol: str) -> Optional[NestedOptionChain]:
        """Get option chain for a symbol"""
        try:
            chain = get_option_chain(self.session, symbol)
            return chain
        except Exception as e:
            logger.error(f"Error getting option chain for {symbol}: {e}")
            return None
    
    def find_atm_option(self, symbol: str, option_type: str, underlying_price: float, 
                       days_to_exp_min: int = 0, days_to_exp_max: int = 7) -> Optional[Dict]:
        """
        Find at-the-money option
        
        Args:
            symbol: Underlying symbol
            option_type: 'call' or 'put'
            underlying_price: Current price of underlying
            days_to_exp_min: Minimum days to expiration
            days_to_exp_max: Maximum days to expiration
            
        Returns:
            Dictionary with option details or None
        """
        try:
            chain = self.get_option_chain(symbol)
            if not chain:
                return None
            
            # Filter expirations by DTE
            today = datetime.now().date()
            valid_expirations = []
            
            for exp_date_str in chain.expirations:
                exp_date = datetime.strptime(exp_date_str, '%Y-%m-%d').date()
                dte = (exp_date - today).days
                
                if days_to_exp_min <= dte <= days_to_exp_max:
                    valid_expirations.append(exp_date_str)
            
            if not valid_expirations:
                logger.warning(f"No valid expirations found for {symbol}")
                return None
            
            # Use the nearest expiration
            nearest_exp = valid_expirations[0]
            
            # Get strikes for this expiration
            strikes = chain.strikes[nearest_exp]
            
            # Find ATM strike (closest to underlying price)
            atm_strike = min(strikes, key=lambda x: abs(x - underlying_price))
            
            # Build option symbol
            exp_formatted = datetime.strptime(nearest_exp, '%Y-%m-%d').strftime('%y%m%d')
            option_type_code = 'C' if option_type.lower() == 'call' else 'P'
            strike_formatted = f"{int(atm_strike * 1000):08d}"
            option_symbol = f"{symbol.ljust(6)}{exp_formatted}{option_type_code}{strike_formatted}"
            
            return {
                'symbol': option_symbol.replace(' ', ''),
                'underlying': symbol,
                'option_type': option_type.upper(),
                'strike': atm_strike,
                'expiration': nearest_exp,
                'dte': (datetime.strptime(nearest_exp, '%Y-%m-%d').date() - today).days
            }
            
        except Exception as e:
            logger.error(f"Error finding ATM option for {symbol}: {e}")
            return None
    
    def get_option_quote(self, option_symbol: str) -> Optional[Dict]:
        """
        Get current quote for an option
        
        Returns:
            Dictionary with bid, ask, last, mark prices
        """
        try:
            # Use DXFeed to get quote
            from tastytrade.dxfeed import DXFeedStreamer
            
            async_streamer = DXFeedStreamer(self.session)
            
            try:
                # Subscribe and get quote
                quote = async_streamer.get_event(EventType.QUOTE, [option_symbol])
                
                if quote and len(quote) > 0:
                    q = quote[0]
                    bid = getattr(q, 'bidPrice', 0) or 0
                    ask = getattr(q, 'askPrice', 0) or 0
                    last = getattr(q, 'lastPrice', 0) or 0
                    mark = (bid + ask) / 2 if (bid > 0 and ask > 0) else last
                    
                    return {
                        'symbol': option_symbol,
                        'bid': bid,
                        'ask': ask,
                        'last': last,
                        'mark': mark if mark > 0 else 0.01  # Fallback to minimum
                    }
            finally:
                async_streamer.close()
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting quote for {option_symbol}: {e}")
            return None
    
    def get_underlying_price(self, symbol: str) -> Optional[float]:
        """Get current price of underlying symbol"""
        try:
            from tastytrade.dxfeed import DXFeedStreamer
            
            streamer = DXFeedStreamer(self.session)
            
            try:
                quote = streamer.get_event(EventType.QUOTE, [symbol])
                
                if quote and len(quote) > 0:
                    q = quote[0]
                    bid = getattr(q, 'bidPrice', 0) or 0
                    ask = getattr(q, 'askPrice', 0) or 0
                    last = getattr(q, 'lastPrice', 0) or 0
                    
                    # Return mark price (mid of bid-ask), fallback to last
                    if bid > 0 and ask > 0:
                        return (bid + ask) / 2
                    return last if last > 0 else None
            finally:
                streamer.close()
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}")
            return None
    
    def place_order(self, option_symbol: str, quantity: int, action: str = 'BUY', 
                   order_type: str = 'MARKET', limit_price: Optional[float] = None) -> Optional[str]:
        """
        Place an order for an option
        
        Args:
            option_symbol: Option symbol
            quantity: Number of contracts
            action: 'BUY' or 'SELL'
            order_type: 'MARKET' or 'LIMIT'
            limit_price: Limit price (required for LIMIT orders)
            
        Returns:
            Order ID if successful, None otherwise
        """
        try:
            from tastytrade.order import Leg
            
            # Determine order action
            if action.upper() == 'BUY':
                order_action = OrderAction.BUY_TO_OPEN
            else:
                order_action = OrderAction.SELL_TO_CLOSE
            
            # Create leg
            leg = Leg(
                instrument_type='Equity Option',
                symbol=option_symbol,
                quantity=quantity,
                action=order_action
            )
            
            # Create order
            if order_type.upper() == 'LIMIT' and limit_price:
                order = NewOrder(
                    time_in_force=OrderTimeInForce.DAY,
                    order_type=OrderType.LIMIT,
                    legs=[leg],
                    price=limit_price
                )
            else:
                order = NewOrder(
                    time_in_force=OrderTimeInForce.DAY,
                    order_type=OrderType.MARKET,
                    legs=[leg]
                )
            
            # Place order
            response = self.account.place_order(self.session, order, dry_run=False)
            
            if response:
                order_id = response.id if hasattr(response, 'id') else str(response)
                logger.info(f"Order placed: {order_id} for {option_symbol} x{quantity} {action}")
                return order_id
            
            return None
            
        except Exception as e:
            logger.error(f"Error placing order for {option_symbol}: {e}")
            return None
    
    def get_positions(self) -> List[Dict]:
        """Get current positions"""
        try:
            positions = self.account.get_positions(self.session)
            
            result = []
            for pos in positions:
                if pos.instrument_type == 'Equity Option':
                    result.append({
                        'symbol': pos.symbol,
                        'quantity': pos.quantity,
                        'average_price': pos.average_open_price,
                        'current_price': pos.mark_price,
                        'pnl': pos.realized_day_gain_loss
                    })
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    def get_account_balance(self) -> Dict:
        """Get account balance information"""
        try:
            balances = self.account.get_balances(self.session)
            
            return {
                'cash': balances.cash_balance,
                'buying_power': balances.derivative_buying_power,
                'equity': balances.net_liquidating_value,
                'pnl_today': balances.realized_day_gain_loss
            }
            
        except Exception as e:
            logger.error(f"Error getting account balance: {e}")
            return {}

