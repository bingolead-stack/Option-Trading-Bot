"""
FastAPI application for the trading bot dashboard with authentication
Modern async API with automatic documentation
"""
import logging
from typing import List, Optional
from datetime import datetime, time as dt_time
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from models.database import get_session, Ticker, Trade, BotStatus, PriceCache, AdminSettings
from config.settings import PORT, CORS_ORIGINS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app with automatic documentation
app = FastAPI(
    title="Options Trading Bot API",
    description="Professional trading bot API with dark theme and authentication",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS if isinstance(CORS_ORIGINS, list) else [CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global bot instance (will be set from main)
bot_instance = None


def set_bot_instance(bot):
    """Set the global bot instance"""
    global bot_instance
    bot_instance = bot


def is_market_open() -> bool:
    """Check if market is open (9:30 AM - 4:00 PM ET, Mon-Fri)"""
    now = datetime.now()
    if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False
    market_open = dt_time(9, 30)
    market_close = dt_time(16, 0)
    current_time = now.time()
    return market_open <= current_time <= market_close


# ==================== PYDANTIC MODELS ====================

class PasskeyValidation(BaseModel):
    """Passkey validation request"""
    passkey: str = Field(..., min_length=1, description="Passkey to validate")


class PasskeyChange(BaseModel):
    """Passkey change request"""
    current_passkey: str = Field(..., min_length=1, description="Current passkey")
    new_passkey: str = Field(..., min_length=6, description="New passkey (min 6 characters)")


class TickerCreate(BaseModel):
    """Create ticker request"""
    symbol: str = Field(..., min_length=1, max_length=10, description="Stock symbol")
    threshold: float = Field(0.5, ge=0, le=100, description="Threshold percentage")
    enabled: bool = Field(True, description="Enable ticker immediately")


class TickerUpdate(BaseModel):
    """Update ticker request"""
    enabled: Optional[bool] = Field(None, description="Enable/disable ticker")
    threshold: Optional[float] = Field(None, ge=0, le=100, description="Threshold percentage")
    max_positions: Optional[int] = Field(None, ge=0, description="Max positions")
    capital_per_trade: Optional[float] = Field(None, ge=0, description="Capital per trade")


class TickerToggle(BaseModel):
    """Toggle ticker request"""
    enabled: bool = Field(..., description="Enable/disable ticker")


class TickerResponse(BaseModel):
    """Ticker response"""
    symbol: str
    enabled: bool
    threshold: float
    positions: int = 0
    pnl: float = 0.0

    class Config:
        from_attributes = True


class PositionResponse(BaseModel):
    """Position response"""
    id: str
    symbol: str
    option_type: str
    strike: float
    entry_price: float
    current_price: float
    quantity: int
    pnl: float
    pnl_percent: float
    entry_time: str


class TradeResponse(BaseModel):
    """Trade response"""
    id: str
    symbol: str
    option_type: str
    strike: float
    action: str
    price: float
    quantity: int
    status: str
    pnl: Optional[float] = None
    timestamp: str


class BotStatusResponse(BaseModel):
    """Bot status response"""
    running: bool
    market_open: bool
    today_pnl: float
    total_pnl: float
    positions_count: int
    trades_count: int
    uptime: Optional[str] = None


class StatsResponse(BaseModel):
    """Statistics response"""
    today_pnl: float
    total_pnl: float
    win_rate: float
    total_trades: int
    open_positions: int


class MessageResponse(BaseModel):
    """Generic message response"""
    message: str


class ErrorResponse(BaseModel):
    """Error response"""
    error: str


# ==================== ROOT & HEALTH ====================

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "name": "Options Trading Bot API",
        "version": "2.0.0",
        "framework": "FastAPI",
        "status": "running",
        "features": ["dark_theme", "authentication", "real_time_updates", "async"],
        "docs": "/api/docs"
    }


@app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "bot_running": bot_instance.running if bot_instance else False
    }


# ==================== AUTHENTICATION ====================

@app.post("/api/auth/validate", tags=["Authentication"], status_code=status.HTTP_200_OK)
async def validate_auth(payload: PasskeyValidation):
    """Validate passkey against database"""
    session = get_session()
    try:
        admin = session.query(AdminSettings).first()
        if not admin:
            # Initialize with default passkey if not exists
            admin = AdminSettings(passkey='admin123')
            session.add(admin)
            session.commit()
        
        if payload.passkey == admin.passkey:
            return {"valid": True}
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid passkey"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating passkey: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error validating passkey"
        )
    finally:
        session.close()


@app.post("/api/auth/change-passkey", tags=["Authentication"], response_model=MessageResponse)
async def change_passkey(payload: PasskeyChange):
    """Change passkey (admin only) - stored in database"""
    session = get_session()
    try:
        admin = session.query(AdminSettings).first()
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Admin settings not found"
            )
        
        # Verify current passkey
        if payload.current_passkey != admin.passkey:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid current passkey"
            )
        
        # Validate new passkey
        if len(payload.new_passkey) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New passkey must be at least 6 characters"
            )
        
        # Update passkey in database
        admin.passkey = payload.new_passkey
        admin.updated_at = datetime.utcnow()
        session.commit()
        
        logger.info("Passkey changed successfully (stored in database)")
        
        return {"message": "Passkey changed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing passkey: {e}")
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    finally:
        session.close()


# ==================== BOT CONTROL ====================

@app.get("/api/bot/status", tags=["Bot Control"], response_model=BotStatusResponse)
async def get_bot_status():
    """Get bot status with comprehensive info"""
    session = get_session()
    try:
        # Get bot running status
        running = bot_instance.running if bot_instance else False
        market_open = is_market_open()
        
        # Get trades for stats
        all_trades = session.query(Trade).all()
        today = datetime.now().date()
        today_trades = [t for t in all_trades if t.entry_time and t.entry_time.date() == today]
        
        # Calculate P&L
        total_pnl = sum(t.pnl for t in all_trades if t.pnl)
        today_pnl = sum(t.pnl for t in today_trades if t.pnl)
        
        # Count positions and trades
        open_positions = session.query(Trade).filter_by(status='OPEN').count()
        total_trades = len(all_trades)
        
        return BotStatusResponse(
            running=running,
            market_open=market_open,
            today_pnl=round(today_pnl, 2),
            total_pnl=round(total_pnl, 2),
            positions_count=open_positions,
            trades_count=total_trades,
            uptime=None
        )
        
    except Exception as e:
        logger.error(f"Error getting bot status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    finally:
        session.close()


@app.post("/api/bot/start", tags=["Bot Control"], response_model=MessageResponse)
async def start_bot():
    """Start the trading bot"""
    if not bot_instance:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bot not initialized"
        )
    
    try:
        if bot_instance.running:
            return MessageResponse(message="Bot is already running")
        
        bot_instance.start()
        logger.info("Bot started via API")
        
        return MessageResponse(message="Bot started successfully")
        
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/api/bot/stop", tags=["Bot Control"], response_model=MessageResponse)
async def stop_bot():
    """Stop the trading bot"""
    if not bot_instance:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bot not initialized"
        )
    
    try:
        if not bot_instance.running:
            return MessageResponse(message="Bot is already stopped")
        
        bot_instance.stop()
        logger.info("Bot stopped via API")
        
        return MessageResponse(message="Bot stopped successfully")
        
    except Exception as e:
        logger.error(f"Error stopping bot: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ==================== TICKER MANAGEMENT ====================

@app.get("/api/tickers", tags=["Tickers"], response_model=List[TickerResponse])
async def get_tickers():
    """Get all tickers with stats"""
    session = get_session()
    try:
        tickers = session.query(Ticker).all()
        result = []
        
        for t in tickers:
            # Get positions and P&L for this ticker
            ticker_trades = session.query(Trade).filter_by(ticker=t.symbol).all()
            positions = len([tr for tr in ticker_trades if tr.status == 'OPEN'])
            pnl = sum(tr.pnl for tr in ticker_trades if tr.pnl)
            
            result.append(TickerResponse(
                symbol=t.symbol,
                enabled=t.enabled,
                threshold=t.threshold,
                positions=positions,
                pnl=round(pnl, 2)
            ))
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting tickers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    finally:
        session.close()


@app.post("/api/tickers", tags=["Tickers"], response_model=TickerResponse, status_code=status.HTTP_201_CREATED)
async def add_ticker(payload: TickerCreate):
    """Add a new ticker"""
    session = get_session()
    try:
        symbol = payload.symbol.upper().strip()
        
        if not symbol:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Symbol is required"
            )
        
        # Check if ticker already exists
        existing = session.query(Ticker).filter_by(symbol=symbol).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ticker already exists"
            )
        
        ticker = Ticker(
            symbol=symbol,
            enabled=payload.enabled,
            threshold=payload.threshold,
            max_positions=2,
            capital_per_trade=500
        )
        
        session.add(ticker)
        session.commit()
        
        logger.info(f"Added ticker: {symbol}")
        
        return TickerResponse(
            symbol=ticker.symbol,
            enabled=ticker.enabled,
            threshold=ticker.threshold,
            positions=0,
            pnl=0.0
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding ticker: {e}")
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    finally:
        session.close()


@app.put("/api/tickers/{symbol}", tags=["Tickers"], response_model=TickerResponse)
async def update_ticker(symbol: str, payload: TickerUpdate):
    """Update a ticker by symbol"""
    session = get_session()
    try:
        ticker = session.query(Ticker).filter_by(symbol=symbol.upper()).first()
        if not ticker:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticker not found"
            )
        
        if payload.enabled is not None:
            ticker.enabled = payload.enabled
        if payload.threshold is not None:
            ticker.threshold = payload.threshold
        if payload.max_positions is not None:
            ticker.max_positions = payload.max_positions
        if payload.capital_per_trade is not None:
            ticker.capital_per_trade = payload.capital_per_trade
        
        ticker.updated_at = datetime.utcnow()
        session.commit()
        
        logger.info(f"Updated ticker: {ticker.symbol}")
        
        return TickerResponse(
            symbol=ticker.symbol,
            enabled=ticker.enabled,
            threshold=ticker.threshold,
            positions=0,
            pnl=0.0
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating ticker: {e}")
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    finally:
        session.close()


@app.delete("/api/tickers/{symbol}", tags=["Tickers"], response_model=MessageResponse)
async def delete_ticker(symbol: str):
    """Delete a ticker by symbol"""
    session = get_session()
    try:
        ticker = session.query(Ticker).filter_by(symbol=symbol.upper()).first()
        if not ticker:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticker not found"
            )
        
        session.delete(ticker)
        session.commit()
        
        logger.info(f"Deleted ticker: {symbol}")
        
        return MessageResponse(message="Ticker deleted")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting ticker: {e}")
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    finally:
        session.close()


@app.patch("/api/tickers/{symbol}/toggle", tags=["Tickers"], response_model=TickerResponse)
async def toggle_ticker(symbol: str, payload: TickerToggle):
    """Toggle ticker enabled status"""
    session = get_session()
    try:
        ticker = session.query(Ticker).filter_by(symbol=symbol.upper()).first()
        if not ticker:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticker not found"
            )
        
        ticker.enabled = payload.enabled
        ticker.updated_at = datetime.utcnow()
        session.commit()
        
        logger.info(f"Toggled ticker {symbol}: {ticker.enabled}")
        
        return TickerResponse(
            symbol=ticker.symbol,
            enabled=ticker.enabled,
            threshold=ticker.threshold,
            positions=0,
            pnl=0.0
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling ticker: {e}")
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    finally:
        session.close()


# ==================== POSITIONS ====================

@app.get("/api/positions", tags=["Positions"], response_model=List[PositionResponse])
async def get_positions():
    """Get all open positions"""
    session = get_session()
    try:
        trades = session.query(Trade).filter_by(status='OPEN').all()
        
        positions = []
        for t in trades:
            # Get current price (use exit_price as current for demo, or fetch from API)
            current_price = t.exit_price if t.exit_price else t.entry_price
            pnl = (current_price - t.entry_price) * t.quantity * 100
            pnl_percent = ((current_price - t.entry_price) / t.entry_price) * 100 if t.entry_price else 0
            
            positions.append(PositionResponse(
                id=str(t.id),
                symbol=t.ticker,
                option_type=t.option_type,
                strike=t.strike,
                entry_price=t.entry_price,
                current_price=current_price,
                quantity=t.quantity,
                pnl=round(pnl, 2),
                pnl_percent=round(pnl_percent, 2),
                entry_time=t.entry_time.isoformat() if t.entry_time else ""
            ))
        
        return positions
        
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    finally:
        session.close()


@app.post("/api/positions/{position_id}/close", tags=["Positions"])
async def close_position(position_id: int):
    """Close a position"""
    session = get_session()
    try:
        trade = session.query(Trade).get(position_id)
        if not trade:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Position not found"
            )
        
        if trade.status != 'OPEN':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Position is not open"
            )
        
        # Use entry price + 1% for demo (in production, fetch real price)
        exit_price = trade.entry_price * 1.01
        
        trade.exit_price = exit_price
        trade.exit_time = datetime.utcnow()
        trade.status = 'CLOSED'
        trade.pnl = (exit_price - trade.entry_price) * trade.quantity * 100
        
        session.commit()
        
        logger.info(f"Closed position {position_id} with P&L: ${trade.pnl:.2f}")
        
        return {
            "id": str(trade.id),
            "status": trade.status,
            "pnl": round(trade.pnl, 2)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error closing position: {e}")
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    finally:
        session.close()


# ==================== TRADES ====================

@app.get("/api/trades", tags=["Trades"], response_model=List[TradeResponse])
async def get_trades(filter: str = "all"):
    """Get trades with optional filter (all, open, closed)"""
    session = get_session()
    try:
        query = session.query(Trade)
        
        if filter == 'open':
            query = query.filter_by(status='OPEN')
        elif filter == 'closed':
            query = query.filter_by(status='CLOSED')
        
        trades = query.order_by(Trade.entry_time.desc()).limit(100).all()
        
        result = []
        for t in trades:
            result.append(TradeResponse(
                id=str(t.id),
                symbol=t.ticker,
                option_type=t.option_type,
                strike=t.strike,
                action='BUY' if t.status == 'OPEN' or not t.exit_price else 'SELL',
                price=t.entry_price if t.status == 'OPEN' else t.exit_price,
                quantity=t.quantity,
                status=t.status,
                pnl=round(t.pnl, 2) if t.pnl else None,
                timestamp=t.entry_time.isoformat() if t.entry_time else ""
            ))
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting trades: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    finally:
        session.close()


# ==================== STATISTICS ====================

@app.get("/api/stats", tags=["Statistics"], response_model=StatsResponse)
async def get_stats():
    """Get trading statistics"""
    session = get_session()
    try:
        all_trades = session.query(Trade).all()
        today = datetime.now().date()
        
        # Calculate stats
        total_trades = len(all_trades)
        open_positions = len([t for t in all_trades if t.status == 'OPEN'])
        
        # P&L calculations
        total_pnl = sum(t.pnl for t in all_trades if t.pnl)
        today_trades = [t for t in all_trades if t.entry_time and t.entry_time.date() == today]
        today_pnl = sum(t.pnl for t in today_trades if t.pnl)
        
        # Win rate
        closed_trades = [t for t in all_trades if t.status == 'CLOSED' and t.pnl is not None]
        winning_trades = len([t for t in closed_trades if t.pnl > 0])
        win_rate = (winning_trades / len(closed_trades) * 100) if closed_trades else 0
        
        return StatsResponse(
            today_pnl=round(today_pnl, 2),
            total_pnl=round(total_pnl, 2),
            win_rate=round(win_rate, 1),
            total_trades=total_trades,
            open_positions=open_positions
        )
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    finally:
        session.close()


# ==================== ERROR HANDLERS ====================

@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Handle 404 errors"""
    return {"error": "Not found"}


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Handle 500 errors"""
    return {"error": "Internal server error"}


# For development
if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=PORT)
