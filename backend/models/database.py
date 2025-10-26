"""
Database models and management
"""
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from datetime import datetime
import os

Base = declarative_base()


class Ticker(Base):
    """Ticker configuration model"""
    __tablename__ = 'tickers'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), unique=True, nullable=False)
    enabled = Column(Boolean, default=True)
    threshold = Column(Float, default=0.5)  # Percentage threshold
    max_positions = Column(Integer, default=2)
    capital_per_trade = Column(Float, default=500)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Trade(Base):
    """Trade history model"""
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True)
    ticker = Column(String(10), nullable=False)
    option_type = Column(String(4), nullable=False)  # CALL or PUT
    option_symbol = Column(String(50), nullable=False)
    strike = Column(Float, nullable=False)
    expiration = Column(String(10), nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float)
    quantity = Column(Integer, nullable=False)
    status = Column(String(20), default='OPEN')  # OPEN, CLOSED, CANCELLED
    pnl = Column(Float, default=0.0)
    open_price_ref = Column(Float)  # Reference open price that triggered trade
    entry_time = Column(DateTime, default=datetime.utcnow)
    exit_time = Column(DateTime)
    order_id = Column(String(50))
    notes = Column(String(500))


class BotStatus(Base):
    """Bot status and configuration"""
    __tablename__ = 'bot_status'
    
    id = Column(Integer, primary_key=True)
    is_running = Column(Boolean, default=False)
    paper_trading = Column(Boolean, default=True)
    daily_pnl = Column(Float, default=0.0)
    total_trades_today = Column(Integer, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow)
    config = Column(JSON)  # Store additional configuration


class AdminSettings(Base):
    """Admin settings including passkey"""
    __tablename__ = 'admin_settings'
    
    id = Column(Integer, primary_key=True)
    passkey = Column(String(255), nullable=False, default='admin123')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PriceCache(Base):
    """Cache for option prices and open prices (5-minute intervals)"""
    __tablename__ = 'price_cache'
    
    id = Column(Integer, primary_key=True)
    ticker = Column(String(10), nullable=False)
    option_symbol = Column(String(50), nullable=False)
    option_type = Column(String(4), nullable=False)
    strike = Column(Float, nullable=False)
    expiration = Column(String(10), nullable=False)
    open_price = Column(Float)  # Open price at market open (9:30 ET)
    current_price = Column(Float)
    high_price = Column(Float)
    low_price = Column(Float)
    underlying_price = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    date = Column(String(10))  # YYYY-MM-DD for daily open prices
    interval_time = Column(String(5))  # HH:MM for 5-minute interval tracking


class DatabaseManager:
    """Database manager singleton"""
    
    _instance = None
    _engine = None
    _session_factory = None
    
    def __new__(cls, db_path=None):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, db_path=None):
        if self._engine is None:
            if db_path is None:
                from config.settings import DATABASE_PATH
                db_path = DATABASE_PATH
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            
            self._engine = create_engine(f'sqlite:///{db_path}', echo=False)
            self._session_factory = sessionmaker(bind=self._engine)
            self.Session = scoped_session(self._session_factory)
            
            # Create tables
            Base.metadata.create_all(self._engine)
            
            # Initialize bot status if not exists
            self._init_bot_status()
    
    def _init_bot_status(self):
        """Initialize bot status record and admin settings"""
        session = self.Session()
        try:
            # Initialize bot status
            status = session.query(BotStatus).first()
            if not status:
                status = BotStatus(
                    is_running=False,
                    paper_trading=True,
                    daily_pnl=0.0,
                    total_trades_today=0,
                    config={}
                )
                session.add(status)
            
            # Initialize admin settings with default passkey
            admin = session.query(AdminSettings).first()
            if not admin:
                admin = AdminSettings(
                    passkey='admin123'  # Default passkey
                )
                session.add(admin)
            
            session.commit()
        finally:
            session.close()
    
    def get_session(self):
        """Get a new database session"""
        return self.Session()
    
    def close_session(self, session):
        """Close a database session"""
        session.close()


# Convenience functions
def get_db():
    """Get database manager instance"""
    return DatabaseManager()


def get_session():
    """Get a new database session"""
    return get_db().get_session()

