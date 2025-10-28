"""
TastyTrade API Client Wrapper
Handles connection to TastyTrade API and option trading operations
"""
import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from decimal import Decimal
from tastytrade import Session, Account
from tastytrade import DXLinkStreamer
from tastytrade.dxfeed import Quote
from tastytrade.instruments import get_option_chain, Option
from tastytrade.order import NewOrder, OrderAction, OrderTimeInForce, OrderType, PriceEffect, OrderStatus
import time

logger = logging.getLogger(__name__)


class TastyClient:
    """Wrapper for TastyTrade API"""
    
    def __init__(self, client_secret: str, refresh_token: str, account_number: str, paper_trading: bool = True):
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.account_number = account_number
        self.paper_trading = paper_trading
        self.session = None
        self.account = None
        
    def connect(self) -> bool:
        """Connect to TastyTrade API"""
        try:
            # Create session with OAuth credentials
            # In tastytrade 11.0.0, Session uses OAuth with provider_secret and refresh_token
            # Use is_test parameter to specify environment
            self.session = Session(
                self.client_secret, 
                self.refresh_token,
                is_test=self.paper_trading
            )
            
            # Set reasonable timeouts on the httpx clients to prevent hanging
            # Default is 5 seconds, but option chains can be large
            self.session.sync_client.timeout = 30.0  # 30 second timeout
            self.session.async_client.timeout = 30.0
            
            if self.paper_trading:
                logger.info("Connected to TastyTrade Certification (Paper) environment")
            else:
                logger.info("Connected to TastyTrade Production environment")
            
            # Get account (Account.get returns a list in v11.0.0)
            accounts = Account.get(self.session)
            
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
    
    def get_option_chain(self, symbol: str) -> Optional[Dict]:
        """Get option chain for a symbol (returns dict[date, list[Option]])"""
        try:
            logger.debug(f"Fetching option chain for {symbol}")
            chain = get_option_chain(self.session, symbol)
            
            if chain:
                logger.debug(f"Retrieved option chain with {len(chain)} expirations")
                # Log first few expirations for debugging
                for i, (exp_date, opts) in enumerate(sorted(chain.items())[:3]):
                    logger.debug(f"  Expiration {i+1}: {exp_date} with {len(opts)} options")
            else:
                logger.warning(f"Empty option chain returned for {symbol}")
            
            return chain
        except Exception as e:
            logger.error(f"Error getting option chain for {symbol}: {e}", exc_info=True)
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
            logger.debug(f"Finding ATM {option_type} for {symbol}, underlying_price={underlying_price}, DTE range={days_to_exp_min}-{days_to_exp_max}")
            
            chain = self.get_option_chain(symbol)
            if not chain:
                logger.warning(f"No option chain returned for {symbol}")
                return None
            
            logger.debug(f"Option chain has {len(chain)} expiration dates")
            
            # Filter expirations by DTE
            # chain is now dict[date, list[Option]]
            today = datetime.now().date()
            valid_options = []
            
            # Map option_type string to OptionType enum value ('C' or 'P')
            target_type = 'C' if option_type.upper() == 'CALL' else 'P'
            
            for exp_date, options_list in sorted(chain.items()):
                dte = (exp_date - today).days
                
                if days_to_exp_min <= dte <= days_to_exp_max:
                    # Filter by option type ('C' or 'P')
                    for option in options_list:
                        if option.option_type.value == target_type:
                            valid_options.append(option)
                            # Only log first few to avoid spam
                            if len(valid_options) <= 5 or len(valid_options) == len(options_list) // 2:
                                logger.debug(f"      Added {option_type} strike={option.strike_price}")
            
            if not valid_options:
                logger.warning(f"No valid options found for {symbol} {option_type} (checked {len(chain)} expirations)")
                return None
            
            logger.debug(f"Found {len(valid_options)} valid {option_type} options")
            
            # Find ATM option (closest strike to underlying price)
            atm_option = min(valid_options, key=lambda opt: abs(float(opt.strike_price) - float(underlying_price)))
            
            # Calculate DTE
            dte = (atm_option.expiration_date - today).days
            
            logger.debug(
                f"Selected ATM {option_type}: strike={atm_option.strike_price}, "
                f"expiration={atm_option.expiration_date}, DTE={dte}, "
                f"symbol={atm_option.symbol}, streamer_symbol={atm_option.streamer_symbol}"
            )
            
            return {
                'symbol': atm_option.symbol,  # Use OCC symbol format for orders, not streamer_symbol
                'streamer_symbol': atm_option.streamer_symbol,  # Keep for streaming quotes
                'underlying': symbol,
                'option_type': option_type.upper(),
                'strike': float(atm_option.strike_price),
                'expiration': atm_option.expiration_date.strftime('%Y-%m-%d'),
                'dte': dte
            }
            
        except Exception as e:
            logger.error(f"Error finding ATM option for {symbol}: {e}", exc_info=True)
            return None
    
    async def _get_quote_async(self, symbol: str) -> Optional[Quote]:
        """
        Async helper to get quote from DXLinkStreamer
        
        Args:
            symbol: Symbol to get quote for
            
        Returns:
            Quote object or None
        """
        try:
            async with DXLinkStreamer(self.session) as streamer:
                await streamer.subscribe(Quote, [symbol])
                # Add timeout to prevent hanging (10 seconds)
                quote = await asyncio.wait_for(streamer.get_event(Quote), timeout=10.0)
                return quote
        except asyncio.TimeoutError:
            logger.warning(f"Timeout getting quote for {symbol} after 10 seconds")
            return None
        except Exception as e:
            logger.error(f"Error getting quote for {symbol}: {e}")
            return None
    
    def get_option_quote(self, option_symbol: str) -> Optional[Dict]:
        """
        Get current quote for an option
        
        Args:
            option_symbol: Can be either OCC format or streamer symbol format
        
        Returns:
            Dictionary with bid, ask, last, mark prices
        """
        try:
            # Convert OCC symbol to streamer symbol if needed
            # Streamer symbols start with '.' (e.g., .SPY251031C687)
            # OCC symbols do not (e.g., SPY   251031C00687000)
            if not option_symbol.startswith('.'):
                # It's an OCC symbol, convert to streamer format
                from tastytrade.instruments import Option
                streamer_symbol = Option.occ_to_streamer_symbol(option_symbol)
                logger.debug(f"Converted OCC symbol {option_symbol} to streamer symbol {streamer_symbol}")
            else:
                streamer_symbol = option_symbol
            
            logger.debug(f"Fetching option quote for {streamer_symbol}")
            # Run async method - asyncio.run() creates a new event loop
            quote = asyncio.run(self._get_quote_async(streamer_symbol))
            
            if quote:
                bid = getattr(quote, 'bid_price', 0) or 0
                ask = getattr(quote, 'ask_price', 0) or 0
                last = getattr(quote, 'last_price', 0) or 0
                mark = (bid + ask) / 2 if (bid > 0 and ask > 0) else last
                
                logger.debug(f"Option quote: bid={bid}, ask={ask}, mark={mark}")
                
                return {
                    'symbol': streamer_symbol,
                    'bid': bid,
                    'ask': ask,
                    'last': last,
                    'mark': mark if mark > 0 else 0.01  # Fallback to minimum
                }
            else:
                logger.warning(f"No quote returned for option {streamer_symbol}")
                return None
            
        except Exception as e:
            logger.error(f"Error getting quote for {option_symbol}: {e}", exc_info=True)
            return None
    
    def get_underlying_price(self, symbol: str) -> Optional[float]:
        """Get current price of underlying symbol"""
        try:
            logger.debug(f"Fetching quote for {symbol}")
            # Run async method - asyncio.run() creates a new event loop
            quote = asyncio.run(self._get_quote_async(symbol))
            
            if quote:
                bid = getattr(quote, 'bid_price', 0) or 0
                ask = getattr(quote, 'ask_price', 0) or 0
                last = getattr(quote, 'last_price', 0) or 0
                
                # Return mark price (mid of bid-ask), fallback to last
                if bid > 0 and ask > 0:
                    price = (bid + ask) / 2
                    logger.debug(f"{symbol} quote: bid={bid}, ask={ask}, mark={price}")
                    return price
                elif last > 0:
                    logger.debug(f"{symbol} quote: last={last} (no bid/ask)")
                    return last
                else:
                    logger.warning(f"{symbol} quote has no valid prices: bid={bid}, ask={ask}, last={last}")
                    return None
            else:
                logger.warning(f"No quote returned for {symbol}")
                return None
            
        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}", exc_info=True)
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
                quantity=Decimal(str(quantity)),
                action=order_action
            )
            
            # Create order
            if order_type.upper() == 'LIMIT' and limit_price:
                order = NewOrder(
                    time_in_force=OrderTimeInForce.DAY,
                    order_type=OrderType.LIMIT,
                    legs=[leg],
                    price=Decimal(str(limit_price))
                )
            else:
                order = NewOrder(
                    time_in_force=OrderTimeInForce.DAY,
                    order_type=OrderType.MARKET,
                    legs=[leg]
                )
            
            env_type = "PAPER" if self.paper_trading else "LIVE"
            logger.info(f"Placing {env_type} order: {action} {quantity}x {option_symbol}")
            
            response = self.account.place_order(self.session, order, dry_run=True)
            
            if response:
                # Extract order ID from response
                if hasattr(response, 'order') and hasattr(response.order, 'id'):
                    order_id = response.order.id
                elif hasattr(response, 'id'):
                    order_id = response.id
                else:
                    order_id = str(response)
                
                logger.info(f"✓ {env_type} order placed successfully: ID={order_id}, {option_symbol} x{quantity} {action}")
                return str(order_id)
            
            return None
            
        except Exception as e:
            logger.error(f"Error placing order for {option_symbol}: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
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

