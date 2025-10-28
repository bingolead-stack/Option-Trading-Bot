"""
TastyTrade API Client - Direct API Implementation with OAuth
Handles connection to TastyTrade API using direct HTTP calls with OAuth token management
"""
import logging
import httpx
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from decimal import Decimal
import time
import json

logger = logging.getLogger(__name__)


class TastyClient:
    """Direct API client for TastyTrade with OAuth token management"""
    
    # API Base URLs
    CERT_BASE_URL = "https://api.cert.tastyworks.com"  # Paper trading
    PROD_BASE_URL = "https://api.tastyworks.com"  # Live trading
    
    def __init__(self, client_secret: str, refresh_token: str, account_number: str, paper_trading: bool = True):
        """
        Initialize TastyTrade API client with OAuth
        
        Args:
            client_secret: OAuth client secret (provider_secret)
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
        
        # HTTP client with reasonable timeouts
        self.client = httpx.Client(timeout=30.0)
        
        # Account info
        self.account = None
        
    def __del__(self):
        """Clean up HTTP clients"""
        try:
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
        return datetime.now() >= self.token_expires_at - timedelta(minutes=12)
    
    def _get_access_token(self) -> bool:
        """
        Get access token using OAuth client credentials and refresh token
        
        Returns:
            True if token obtained successfully
        """
        try:
            url = f"{self.base_url}/oauth/token"
            
            # OAuth authentication payload
            payload = {
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "client_secret": self.client_secret
            }
            
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            
            logger.info(f"Getting OAuth token from TastyTrade {'Certification (Paper)' if self.paper_trading else 'Production'} environment...")
            
            response = self.client.post(url, json=payload, headers=headers)
            
            if response.status_code != 200:
                logger.error(f"OAuth token request failed: {response.status_code} - {response.text}")
                return False
            
            data = response.json()
            
            if 'access_token' in data:
                self.session_token = data.get('access_token')
                expires_in = data.get('expires_in')
                
                # Token typically expires after 24 hours
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
        # Check if token exists and is not expired
        if self.session_token and not self._is_token_expired():
            return True
        
        # Need to get new token
        logger.info("Session token missing or expired, obtaining new token...")
        return self._get_access_token()
    
    def connect(self) -> bool:
        """
        Connect to TastyTrade API and load account
        
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
            return True
            
        except Exception as e:
            logger.error(f"Connection error: {e}", exc_info=True)
            return False
    
    def get_option_chain(self, symbol: str) -> Optional[Dict]:
        """
        Get option chain for a symbol
        
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
            
            # The response structure has items, each with expirations
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
    
    def _categorize_symbols(self, symbols: List[str]) -> Dict[str, List[str]]:
        """
        Categorize symbols by type (equity or equity-option)
        
        Args:
            symbols: List of symbols
            
        Returns:
            Dict with 'equity' and 'equity-option' lists
        """
        categorized = {'equity': [], 'equity-option': []}
        
        for symbol in symbols:
            # Option symbols contain spaces (e.g., "SPY   251031C00370000")
            # or are in streamer format starting with . (e.g., ".SPY251031C370")
            if ' ' in symbol or (symbol.startswith('.') and len(symbol) > 10):
                # Remove leading dot if present (streamer format)
                clean_symbol = symbol[1:] if symbol.startswith('.') else symbol
                categorized['equity-option'].append(clean_symbol)
            else:
                categorized['equity'].append(symbol)
        
        return categorized
    
    def get_market_data(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Get market data (quotes) for symbols using REST API
        Uses /market-data/by-type endpoint
        
        Args:
            symbols: List of symbols (can be stocks or option symbols)
            
        Returns:
            Dict mapping symbol to quote data
        """
        try:
            if not self._ensure_authenticated():
                logger.error("Not authenticated")
                return {}
            
            if not symbols:
                return {}
            
            # Categorize symbols by type
            categorized = self._categorize_symbols(symbols)
            
            # Build query parameters
            params = {}
            if categorized['equity']:
                params['equity'] = ','.join(categorized['equity'])
            if categorized['equity-option']:
                params['equity-option'] = ','.join(categorized['equity-option'])
            
            # TastyTrade market data endpoint
            url = f"{self.base_url}/market-data/by-type"
            
            response = self.client.get(url, params=params, headers=self._get_headers())
            
            if response.status_code != 200:
                logger.warning(f"Market data request failed: {response.status_code} - {response.text}")
                return {}
            
            data = response.json()
            items = data.get('data', {}).get('items', [])
            
            result = {}
            for item in items:
                symbol = item.get('symbol')
                if symbol:
                    # Parse numeric fields safely
                    bid = float(item.get('bid', 0) or 0)
                    ask = float(item.get('ask', 0) or 0)
                    last = float(item.get('last', 0) or 0)
                    mark = float(item.get('mark', 0) or 0)
                    
                    result[symbol] = {
                        'bid': bid,
                        'ask': ask,
                        'last': last,
                        'mark': mark
                    }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting market data: {e}", exc_info=True)
            return {}
    
    
    def get_option_quote(self, option_symbol: str) -> Optional[Dict]:
        """
        Get current quote for an option
        
        Args:
            option_symbol: Option symbol (OCC format with spaces or streamer format)
                          Examples: "SPY   251031C00370000" or ".SPY251031C370"
            
        Returns:
            Dictionary with bid, ask, last, mark prices
        """
        try:
            # Get quote using the market data endpoint
            quotes = self.get_market_data([option_symbol])
            
            # The API returns the symbol without the leading dot
            clean_symbol = option_symbol[1:] if option_symbol.startswith('.') else option_symbol
            
            if clean_symbol in quotes:
                quote = quotes[clean_symbol]
                bid = quote.get('bid', 0) or 0
                ask = quote.get('ask', 0) or 0
                last = quote.get('last', 0) or 0
                mark = quote.get('mark', 0) or 0
                
                # Calculate mark if not provided
                if mark == 0 and bid > 0 and ask > 0:
                    mark = (bid + ask) / 2
                elif mark == 0:
                    mark = last
                
                return {
                    'symbol': clean_symbol,
                    'bid': bid,
                    'ask': ask,
                    'last': last,
                    'mark': mark if mark > 0 else 0.01
                }
            else:
                logger.warning(f"No quote data for {option_symbol}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting option quote: {e}", exc_info=True)
            return None
    
    def get_underlying_price(self, symbol: str) -> Optional[float]:
        """
        Get current price of underlying symbol
        
        Args:
            symbol: Underlying ticker symbol
            
        Returns:
            Current price or None
        """
        try:
            quotes = self.get_market_data([symbol])
            
            if symbol in quotes:
                quote = quotes[symbol]
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
                    logger.warning(f"{symbol}: no valid price data")
                    return None
            else:
                logger.warning(f"No quote for {symbol}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}", exc_info=True)
            return None
    
    def place_order(self, option_symbol: str, quantity: int, action: str = 'BUY',
                   order_type: str = 'MARKET', limit_price: Optional[float] = None) -> Optional[str]:
        """
        Place an order for an option
        
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
                return "DRY_RUN_" + str(int(time.time()))  # Fallback ID for dry-run
            
        except Exception as e:
            logger.error(f"Error placing order: {e}", exc_info=True)
            return None
    
    def get_positions(self) -> List[Dict]:
        """
        Get current positions
        
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
        Get account balance information
        
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
