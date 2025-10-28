"""
TastyTrade API Client - Direct API with WebSocket Streaming
Handles OAuth authentication and DXLink WebSocket streaming for live market data
"""
import logging
import httpx
import asyncio
import websockets
import json
import ssl
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
from decimal import Decimal
import time
import threading

logger = logging.getLogger(__name__)


class TastyClient:
    """Direct API client for TastyTrade with WebSocket streaming for market data"""
    
    # API Base URLs
    CERT_BASE_URL = "https://api.cert.tastyworks.com"  # Paper trading
    PROD_BASE_URL = "https://api.tastyworks.com"  # Live trading
    
    def __init__(self, client_secret: str, refresh_token: str, account_number: str, paper_trading: bool = True):
        """
        Initialize TastyTrade API client with WebSocket streaming
        
        Args:
            client_secret: OAuth client secret
            refresh_token: OAuth refresh token
            account_number: Account number
            paper_trading: Use paper trading environment if True
        """
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.account_number = account_number
        self.paper_trading = paper_trading
        
        # API endpoints
        self.base_url = self.CERT_BASE_URL if paper_trading else self.PROD_BASE_URL
        
        # Session management
        self.session_token = None
        self.token_expires_at = None
        
        # HTTP client
        self.client = httpx.Client(timeout=30.0)
        
        # WebSocket streaming
        self.ws = None
        self.dxlink_url = None
        self.dxlink_token = None
        self.ws_channel = 1  # Channel for market data
        self.quote_cache = {}  # Cache latest quotes
        self.subscribed_symbols = set()  # Track subscribed symbols
        self.ws_task = None
        self.ws_loop = None
        self.keepalive_task = None
        
        # Account info
        self.account = None
        
    def __del__(self):
        """Clean up resources"""
        try:
            if self.ws:
                asyncio.run(self._close_websocket())
            self.client.close()
        except:
            pass
    
    def _get_headers(self, include_auth: bool = True) -> dict:
        """Get headers for API requests"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if include_auth and self.session_token:
            headers["Authorization"] = f"Bearer {self.session_token}"
        return headers
    
    def _is_token_expired(self) -> bool:
        """Check if current token is expired or about to expire"""
        if not self.token_expires_at:
            return True
        # Refresh if token expires in less than 10 minutes
        return datetime.now() >= self.token_expires_at - timedelta(minutes=10)
    
    def _get_access_token(self) -> bool:
        """
        Get access token using OAuth
        
        Returns:
            True if token obtained successfully
        """
        try:
            url = f"{self.base_url}/oauth/token"
            
            payload = {
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "client_secret": self.client_secret
            }
            
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            logger.info(f"Getting OAuth token from TastyTrade {'Certification (Paper)' if self.paper_trading else 'Production'} environment...")
            
            response = self.client.post(url, json=payload, headers=headers)
            
            if response.status_code != 200:
                logger.error(f"OAuth token request failed: {response.status_code} - {response.text}")
                return False
            
            data = response.json()
            
            if 'access_token' in data:
                self.session_token = data.get('access_token')
                expires_in = data.get('expires_in', 86400)  # Default 24 hours
                
                self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                
                logger.info("Successfully obtained OAuth access token")
                return True
            else:
                logger.error(f"Invalid OAuth response format: {data}")
                return False
                
        except Exception as e:
            logger.error(f"OAuth token error: {e}", exc_info=True)
            return False
    
    def _ensure_authenticated(self) -> bool:
        """
        Ensure we have a valid session token, refresh if needed
        
        Returns:
            True if authenticated
        """
        if self.session_token and not self._is_token_expired():
            return True
        
        logger.info("Session token missing or expired, obtaining new token...")
        return self._get_access_token()
    
    def _get_dxlink_token(self) -> bool:
        """
        Get DXLink WebSocket token for streaming
        
        Returns:
            True if token obtained
        """
        try:
            if not self._ensure_authenticated():
                return False
            
            url = f"{self.base_url}/api-quote-tokens"
            response = self.client.get(url, headers=self._get_headers())
            
            if response.status_code != 200:
                logger.error(f"Failed to get DXLink token: {response.status_code} - {response.text}")
                return False
            
            data = response.json()
            token_data = data.get('data', {})
            
            self.dxlink_token = token_data.get('token')
            self.dxlink_url = token_data.get('dxlink-url')
            
            if not self.dxlink_token or not self.dxlink_url:
                logger.error(f"Invalid DXLink token response: {data}")
                return False
            
            logger.info(f"Got DXLink token and URL: {self.dxlink_url}")
            return True
            
        except Exception as e:
            logger.error(f"Error getting DXLink token: {e}", exc_info=True)
            return False
    
    async def _websocket_handler(self):
        """Main WebSocket handler loop"""
        try:
            logger.info(f"Connecting to DXLink WebSocket: {self.dxlink_url}")
            
            # Configure SSL context to handle certificate verification
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            async with websockets.connect(self.dxlink_url, ssl=ssl_context) as websocket:
                self.ws = websocket
                
                # Step 1: SETUP
                setup_msg = {
                    "type": "SETUP",
                    "channel": 0,
                    "version": "0.1-DXF-JS/0.3.0",
                    "keepaliveTimeout": 60,
                    "acceptKeepaliveTimeout": 60
                }
                await websocket.send(json.dumps(setup_msg))
                logger.debug(f"Sent SETUP: {setup_msg}")
                
                response = await websocket.recv()
                logger.debug(f"Received: {response}")
                
                # Step 2: Wait for AUTH_STATE and AUTHORIZE
                response = await websocket.recv()
                logger.debug(f"Received: {response}")
                
                auth_msg = {
                    "type": "AUTH",
                    "channel": 0,
                    "token": self.dxlink_token
                }
                await websocket.send(json.dumps(auth_msg))
                logger.debug(f"Sent AUTH")
                
                response = await websocket.recv()
                logger.debug(f"Received: {response}")
                
                # Step 3: CHANNEL_REQUEST
                channel_msg = {
                    "type": "CHANNEL_REQUEST",
                    "channel": self.ws_channel,
                    "service": "FEED",
                    "parameters": {"contract": "AUTO"}
                }
                await websocket.send(json.dumps(channel_msg))
                logger.debug(f"Sent CHANNEL_REQUEST")
                
                response = await websocket.recv()
                logger.debug(f"Received: {response}")
                
                # Step 4: FEED_SETUP
                feed_setup_msg = {
                    "type": "FEED_SETUP",
                    "channel": self.ws_channel,
                    "acceptAggregationPeriod": 0.1,
                    "acceptDataFormat": "COMPACT",
                    "acceptEventFields": {
                        "Quote": ["eventType", "eventSymbol", "bidPrice", "askPrice", "bidSize", "askSize"],
                        "Trade": ["eventType", "eventSymbol", "price", "size", "dayVolume"]
                    }
                }
                await websocket.send(json.dumps(feed_setup_msg))
                logger.debug(f"Sent FEED_SETUP")
                
                response = await websocket.recv()
                logger.debug(f"Received: {response}")
                
                logger.info("✓ WebSocket connection established and configured")
                
                # Start keepalive task
                self.keepalive_task = asyncio.create_task(self._keepalive_loop(websocket))
                
                # Listen for messages
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        await self._handle_message(data)
                    except Exception as e:
                        logger.error(f"Error handling message: {e}")
                        
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket connection closed")
        except Exception as e:
            logger.error(f"WebSocket error: {e}", exc_info=True)
        finally:
            self.ws = None
            if self.keepalive_task:
                self.keepalive_task.cancel()
    
    async def _keepalive_loop(self, websocket):
        """Send keepalive messages every 30 seconds"""
        try:
            while True:
                await asyncio.sleep(30)
                keepalive_msg = {"type": "KEEPALIVE", "channel": 0}
                await websocket.send(json.dumps(keepalive_msg))
                logger.debug("Sent KEEPALIVE")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Keepalive error: {e}")
    
    async def _handle_message(self, data: dict):
        """Handle incoming WebSocket messages"""
        msg_type = data.get('type')
        
        if msg_type == 'FEED_DATA':
            # Parse market data
            channel = data.get('channel')
            feed_data = data.get('data', [])
            
            if not feed_data:
                return
            
            # COMPACT format: ["Quote", [data...]]
            event_type = feed_data[0] if len(feed_data) > 0 else None
            events = feed_data[1] if len(feed_data) > 1 else []
            
            if event_type == "Quote":
                # Parse Quote events
                # Format: ["Quote", symbol, bidPrice, askPrice, bidSize, askSize, ...]
                i = 0
                while i < len(events):
                    if events[i] == "Quote":
                        try:
                            symbol = events[i + 1]
                            bid_price = float(events[i + 2]) if events[i + 2] not in ['NaN', None] else 0
                            ask_price = float(events[i + 3]) if events[i + 3] not in ['NaN', None] else 0
                            
                            # Update cache
                            if symbol not in self.quote_cache:
                                self.quote_cache[symbol] = {}
                            
                            self.quote_cache[symbol].update({
                                'bid': bid_price,
                                'ask': ask_price,
                                'mark': (bid_price + ask_price) / 2 if (bid_price > 0 and ask_price > 0) else 0,
                                'timestamp': time.time()
                            })
                            
                            i += 6  # Move to next quote (Quote type + 5 fields)
                        except (IndexError, ValueError) as e:
                            logger.debug(f"Error parsing quote: {e}")
                            break
                    else:
                        i += 1
            
            elif event_type == "Trade":
                # Parse Trade events for last price
                i = 0
                while i < len(events):
                    if events[i] == "Trade":
                        try:
                            symbol = events[i + 1]
                            last_price = float(events[i + 2]) if events[i + 2] not in ['NaN', None] else 0
                            
                            if symbol not in self.quote_cache:
                                self.quote_cache[symbol] = {}
                            
                            self.quote_cache[symbol].update({
                                'last': last_price,
                                'timestamp': time.time()
                            })
                            
                            i += 5  # Move to next trade
                        except (IndexError, ValueError) as e:
                            logger.debug(f"Error parsing trade: {e}")
                            break
                    else:
                        i += 1
    
    async def _subscribe_symbols(self, symbols: List[str]):
        """Subscribe to symbols on WebSocket"""
        if not self.ws:
            logger.error("WebSocket not connected")
            return False
        
        try:
            # Build subscription list
            add_list = []
            for symbol in symbols:
                if symbol not in self.subscribed_symbols:
                    add_list.append({"type": "Quote", "symbol": symbol})
                    add_list.append({"type": "Trade", "symbol": symbol})
                    self.subscribed_symbols.add(symbol)
            
            if not add_list:
                return True  # Already subscribed
            
            sub_msg = {
                "type": "FEED_SUBSCRIPTION",
                "channel": self.ws_channel,
                "add": add_list
            }
            
            await self.ws.send(json.dumps(sub_msg))
            logger.info(f"Subscribed to {len(symbols)} symbols")
            return True
            
        except Exception as e:
            logger.error(f"Error subscribing to symbols: {e}")
            return False
    
    async def _close_websocket(self):
        """Close WebSocket connection"""
        if self.ws:
            try:
                await self.ws.close()
            except:
                pass
            self.ws = None
        
        if self.keepalive_task:
            self.keepalive_task.cancel()
    
    def _start_websocket_thread(self):
        """Start WebSocket in a separate thread with its own event loop"""
        def run_websocket():
            self.ws_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.ws_loop)
            try:
                self.ws_loop.run_until_complete(self._websocket_handler())
            except Exception as e:
                logger.error(f"WebSocket thread error: {e}")
            finally:
                self.ws_loop.close()
        
        thread = threading.Thread(target=run_websocket, daemon=True)
        thread.start()
        
        # Wait a bit for connection to establish
        time.sleep(3)
    
    def connect(self) -> bool:
        """
        Connect to TastyTrade API and start WebSocket streaming
        
        Returns:
            True if connection successful
        """
        try:
            # Authenticate
            if not self._ensure_authenticated():
                return False
            
            if self.paper_trading:
                logger.info("Connected to TastyTrade Certification (Paper) environment")
            else:
                logger.info("Connected to TastyTrade Production environment")
            
            # Get accounts
            url = f"{self.base_url}/customers/me/accounts"
            response = self.client.get(url, headers=self._get_headers())
            
            if response.status_code != 200:
                logger.error(f"Failed to get accounts: {response.status_code} - {response.text}")
                return False
            
            data = response.json()
            accounts = data.get('data', {}).get('items', [])
            
            if not accounts:
                logger.error("No accounts found")
                return False
            
            # Find the specified account or use the first one
            if self.account_number:
                self.account = next(
                    (acc for acc in accounts if acc.get('account', {}).get('account-number') == self.account_number),
                    None
                )
                if not self.account:
                    logger.error(f"Account {self.account_number} not found")
                    available = [acc.get('account', {}).get('account-number') for acc in accounts]
                    logger.info(f"Available accounts: {available}")
                    return False
            else:
                self.account = accounts[0]
                self.account_number = self.account.get('account', {}).get('account-number')
                logger.info(f"No account specified, using first account: {self.account_number}")
            
            logger.info(f"Account loaded: {self.account_number}")
            
            # Get DXLink token and start WebSocket
            if not self._get_dxlink_token():
                logger.error("Failed to get DXLink token")
                return False
            
            # Start WebSocket connection
            self._start_websocket_thread()
            
            logger.info("✓ TastyTrade API and WebSocket streaming ready")
            return True
            
        except Exception as e:
            logger.error(f"Connection error: {e}", exc_info=True)
            return False
    
    def get_option_chain(self, symbol: str) -> Optional[Dict]:
        """
        Get option chain for a symbol via REST API
        
        Args:
            symbol: Underlying symbol (e.g., 'SPY')
            
        Returns:
            Dict mapping expiration dates to lists of options
        """
        try:
            if not self._ensure_authenticated():
                logger.error("Not authenticated")
                return None
            
            url = f"{self.base_url}/option-chains/{symbol}/nested"
            response = self.client.get(url, headers=self._get_headers())
            
            if response.status_code != 200:
                logger.error(f"Failed to get option chain: {response.status_code} - {response.text}")
                return None
            
            data = response.json()
            items = data.get('data', {}).get('items', [])
            
            if not items:
                logger.warning(f"Empty option chain for {symbol}")
                return {}
            
            # Parse into dict[date, list[option]]
            chain = {}
            
            for item in items:
                expirations = item.get('expirations', [])
                
                for expiration in expirations:
                    exp_date_str = expiration.get('expiration-date')
                    if not exp_date_str:
                        continue
                    
                    exp_date = datetime.strptime(exp_date_str, '%Y-%m-%d').date()
                    dte = expiration.get('days-to-expiration', (exp_date - datetime.now().date()).days)
                    strikes = expiration.get('strikes', [])
                    
                    options = []
                    for strike_item in strikes:
                        strike_price = strike_item.get('strike-price')
                        
                        # Add call option
                        call_symbol = strike_item.get('call')
                        call_streamer = strike_item.get('call-streamer-symbol')
                        if call_symbol:
                            options.append({
                                'symbol': call_symbol,
                                'streamer_symbol': call_streamer,
                                'option_type': 'C',
                                'strike_price': Decimal(str(strike_price)),
                                'expiration_date': exp_date,
                                'dte': dte
                            })
                        
                        # Add put option
                        put_symbol = strike_item.get('put')
                        put_streamer = strike_item.get('put-streamer-symbol')
                        if put_symbol:
                            options.append({
                                'symbol': put_symbol,
                                'streamer_symbol': put_streamer,
                                'option_type': 'P',
                                'strike_price': Decimal(str(strike_price)),
                                'expiration_date': exp_date,
                                'dte': dte
                            })
                    
                    if options:
                        chain[exp_date] = options
            
            logger.debug(f"Retrieved option chain with {len(chain)} expirations")
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
            logger.debug(f"Finding ATM {option_type} for {symbol}, price={underlying_price}, DTE={days_to_exp_min}-{days_to_exp_max}")
            
            chain = self.get_option_chain(symbol)
            if not chain:
                return None
            
            # Filter by option type and DTE
            target_type = 'C' if option_type.upper() == 'CALL' else 'P'
            valid_options = []
            
            for exp_date, options_list in sorted(chain.items()):
                dte = (exp_date - datetime.now().date()).days
                
                if days_to_exp_min <= dte <= days_to_exp_max:
                    for opt in options_list:
                        if opt['option_type'] == target_type:
                            valid_options.append(opt)
            
            if not valid_options:
                logger.warning(f"No valid {option_type} options found for {symbol}")
                return None
            
            logger.debug(f"Found {len(valid_options)} valid {option_type} options")
            
            # Find ATM (closest strike to underlying price)
            atm_option = min(valid_options, key=lambda opt: abs(float(opt['strike_price']) - float(underlying_price)))
            
            return {
                'symbol': atm_option['symbol'],
                'streamer_symbol': atm_option['streamer_symbol'],
                'underlying': symbol,
                'option_type': option_type.upper(),
                'strike': float(atm_option['strike_price']),
                'expiration': atm_option['expiration_date'].strftime('%Y-%m-%d'),
                'dte': atm_option['dte']
            }
            
        except Exception as e:
            logger.error(f"Error finding ATM option: {e}", exc_info=True)
            return None
    
    def _occ_to_streamer(self, occ_symbol: str) -> str:
        """
        Convert OCC option symbol to streamer format
        
        Args:
            occ_symbol: OCC format like "SPY   251031C00370000"
            
        Returns:
            Streamer format like ".SPY251031C370"
        """
        try:
            # Remove extra spaces and parse
            parts = occ_symbol.split()
            if len(parts) != 2:
                return occ_symbol
            
            ticker = parts[0]
            rest = parts[1]
            
            # Format: YYMMDDCPPPPPPP0
            # Extract: date (6), C/P (1), strike (8)
            if len(rest) < 15:
                return occ_symbol
            
            date_part = rest[:6]  # YYMMDD -> YYMMDD
            option_type = rest[6]  # C or P
            strike_raw = rest[7:15]  # 00370000
            
            # Convert strike: 00370000 -> 370
            strike = str(int(strike_raw) / 1000)
            if '.' in strike:
                strike = strike.rstrip('0').rstrip('.')
            
            # Build streamer symbol: .SPY251031C370
            streamer = f".{ticker}{date_part}{option_type}{strike}"
            return streamer
            
        except Exception as e:
            logger.debug(f"Error converting OCC to streamer: {e}")
            return occ_symbol
    
    def get_option_quote(self, option_symbol: str) -> Optional[Dict]:
        """
        Get current quote for an option from WebSocket stream
        
        Args:
            option_symbol: Option symbol (OCC format with spaces or streamer format)
                          Examples: "SPY   251031C00370000" or ".SPY251031C370"
            
        Returns:
            Dictionary with bid, ask, last, mark prices
        """
        try:
            # Use streamer symbol for WebSocket
            if option_symbol.startswith('.'):
                streamer_symbol = option_symbol
            else:
                # Convert OCC to streamer format
                streamer_symbol = self._occ_to_streamer(option_symbol)
            
            # Subscribe to symbol if not already subscribed
            if streamer_symbol not in self.subscribed_symbols:
                if self.ws_loop:
                    asyncio.run_coroutine_threadsafe(
                        self._subscribe_symbols([streamer_symbol]),
                        self.ws_loop
                    )
                    # Wait a bit for subscription
                    time.sleep(0.5)
            
            # Get from cache
            if streamer_symbol in self.quote_cache:
                quote = self.quote_cache[streamer_symbol]
                bid = quote.get('bid', 0) or 0
                ask = quote.get('ask', 0) or 0
                last = quote.get('last', 0) or 0
                mark = quote.get('mark', 0) or 0
                
                # Calculate mark if needed
                if mark == 0 and bid > 0 and ask > 0:
                    mark = (bid + ask) / 2
                elif mark == 0:
                    mark = last
                
                return {
                    'symbol': option_symbol,
                    'bid': bid,
                    'ask': ask,
                    'last': last,
                    'mark': mark if mark > 0 else 0.01
                }
            else:
                logger.warning(f"No cached quote for {option_symbol}, waiting for data...")
                # Wait a bit and try again
                time.sleep(1)
                if streamer_symbol in self.quote_cache:
                    quote = self.quote_cache[streamer_symbol]
                    bid = quote.get('bid', 0) or 0
                    ask = quote.get('ask', 0) or 0
                    last = quote.get('last', 0) or 0
                    mark = (bid + ask) / 2 if (bid > 0 and ask > 0) else last
                    
                    return {
                        'symbol': option_symbol,
                        'bid': bid,
                        'ask': ask,
                        'last': last,
                        'mark': mark if mark > 0 else 0.01
                    }
                return None
                
        except Exception as e:
            logger.error(f"Error getting option quote: {e}", exc_info=True)
            return None
    
    def get_underlying_price(self, symbol: str) -> Optional[float]:
        """
        Get current price of underlying symbol from WebSocket stream
        
        Args:
            symbol: Underlying ticker symbol
            
        Returns:
            Current price or None
        """
        try:
            # Subscribe to symbol if not already subscribed
            if symbol not in self.subscribed_symbols:
                if self.ws_loop:
                    asyncio.run_coroutine_threadsafe(
                        self._subscribe_symbols([symbol]),
                        self.ws_loop
                    )
                    # Wait a bit for subscription
                    time.sleep(0.5)
            
            # Get from cache
            if symbol in self.quote_cache:
                quote = self.quote_cache[symbol]
                bid = quote.get('bid', 0) or 0
                ask = quote.get('ask', 0) or 0
                last = quote.get('last', 0) or 0
                
                if bid > 0 and ask > 0:
                    price = (bid + ask) / 2
                    logger.debug(f"{symbol}: bid={bid}, ask={ask}, mark={price}")
                    return price
                elif last > 0:
                    logger.debug(f"{symbol}: last={last}")
                    return last
                else:
                    logger.warning(f"{symbol}: no valid price data in cache")
                    return None
            else:
                logger.warning(f"No cached quote for {symbol}, waiting for data...")
                # Wait a bit and try again
                time.sleep(1)
                if symbol in self.quote_cache:
                    quote = self.quote_cache[symbol]
                    bid = quote.get('bid', 0) or 0
                    ask = quote.get('ask', 0) or 0
                    last = quote.get('last', 0) or 0
                    
                    if bid > 0 and ask > 0:
                        return (bid + ask) / 2
                    return last if last > 0 else None
                return None
                
        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}", exc_info=True)
            return None
    
    def place_order(self, option_symbol: str, quantity: int, action: str = 'BUY',
                   order_type: str = 'MARKET', limit_price: Optional[float] = None) -> Optional[str]:
        """
        Place an order for an option via REST API
        
        Args:
            option_symbol: Option symbol (OCC format)
            quantity: Number of contracts
            action: 'BUY' or 'SELL'
            order_type: 'MARKET' or 'LIMIT'
            limit_price: Limit price (required for LIMIT orders)
            
        Returns:
            Order ID if successful, None otherwise
        """
        try:
            if not self._ensure_authenticated():
                logger.error("Not authenticated")
                return None
            
            # Prepare order payload
            order_action = "Buy to Open" if action.upper() == 'BUY' else "Sell to Close"
            
            leg = {
                "instrument-type": "Equity Option",
                "symbol": option_symbol,
                "quantity": str(quantity),
                "action": order_action
            }
            
            order_payload = {
                "time-in-force": "Day",
                "order-type": order_type.title(),
                "legs": [leg]
            }
            
            if order_type.upper() == 'LIMIT' and limit_price:
                order_payload["price"] = str(limit_price)
            
            # For dry-run (paper trading simulation)
            order_payload["dry-run"] = True
            
            env_type = "PAPER" if self.paper_trading else "LIVE"
            logger.info(f"Placing {env_type} order: {action} {quantity}x {option_symbol}")
            
            url = f"{self.base_url}/accounts/{self.account_number}/orders"
            response = self.client.post(url, json=order_payload, headers=self._get_headers())
            
            if response.status_code not in [200, 201]:
                logger.error(f"Order placement failed: {response.status_code} - {response.text}")
                return None
            
            data = response.json()
            order_data = data.get('data', {})
            
            # Extract order ID
            if 'order' in order_data:
                order_id = order_data['order'].get('id')
            else:
                order_id = order_data.get('id')
            
            if order_id:
                logger.info(f"✓ {env_type} order placed successfully: ID={order_id}")
                return str(order_id)
            else:
                logger.warning(f"Order response missing ID: {data}")
                return "DRY_RUN_" + str(int(time.time()))
            
        except Exception as e:
            logger.error(f"Error placing order: {e}", exc_info=True)
            return None
    
    def get_positions(self) -> List[Dict]:
        """
        Get current positions via REST API
        
        Returns:
            List of position dictionaries
        """
        try:
            if not self._ensure_authenticated():
                logger.error("Not authenticated")
                return []
            
            url = f"{self.base_url}/accounts/{self.account_number}/positions"
            response = self.client.get(url, headers=self._get_headers())
            
            if response.status_code != 200:
                logger.error(f"Failed to get positions: {response.status_code}")
                return []
            
            data = response.json()
            items = data.get('data', {}).get('items', [])
            
            result = []
            for pos in items:
                if pos.get('instrument-type') == 'Equity Option':
                    result.append({
                        'symbol': pos.get('symbol'),
                        'quantity': pos.get('quantity'),
                        'average_price': pos.get('average-open-price'),
                        'current_price': pos.get('mark-price'),
                        'pnl': pos.get('realized-day-gain-loss', 0)
                    })
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting positions: {e}", exc_info=True)
            return []
    
    def get_account_balance(self) -> Dict:
        """
        Get account balance information via REST API
        
        Returns:
            Dictionary with balance info
        """
        try:
            if not self._ensure_authenticated():
                logger.error("Not authenticated")
                return {}
            
            url = f"{self.base_url}/accounts/{self.account_number}/balances"
            response = self.client.get(url, headers=self._get_headers())
            
            if response.status_code != 200:
                logger.error(f"Failed to get balances: {response.status_code}")
                return {}
            
            data = response.json()
            balance_data = data.get('data', {})
            
            return {
                'cash': balance_data.get('cash-balance', 0),
                'buying_power': balance_data.get('derivative-buying-power', 0),
                'equity': balance_data.get('net-liquidating-value', 0),
                'pnl_today': balance_data.get('realized-day-gain-loss', 0)
            }
            
        except Exception as e:
            logger.error(f"Error getting balance: {e}", exc_info=True)
            return {}
