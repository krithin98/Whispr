import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum
from database import get_db, log_event

class TradeSide(Enum):
    BUY = "buy"
    SELL = "sell"

class TradeStatus(Enum):
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"

class SimulatedTrade:
    """Represents a simulated trade for dry-run testing."""
    
    def __init__(self, symbol: str, side: TradeSide, quantity: int, entry_price: float):
        self.id = None
        self.symbol = symbol
        self.side = side
        self.quantity = quantity
        self.entry_price = entry_price
        self.exit_price = None
        self.entry_time = datetime.utcnow()
        self.exit_time = None
        self.status = TradeStatus.OPEN
        self.pnl = None
        self.pnl_percent = None
    
    def close(self, exit_price: float, exit_time: Optional[datetime] = None):
        """Close the trade and calculate P&L."""
        self.exit_price = exit_price
        self.exit_time = exit_time or datetime.utcnow()
        self.status = TradeStatus.CLOSED
        
        # Calculate P&L
        if self.side == TradeSide.BUY:
            self.pnl = (exit_price - self.entry_price) * self.quantity
        else:  # SELL
            self.pnl = (self.entry_price - exit_price) * self.quantity
        
        self.pnl_percent = (self.pnl / (self.entry_price * self.quantity)) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert trade to dictionary for database storage."""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": self.quantity,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "entry_time": self.entry_time.isoformat(),
            "exit_time": self.exit_time.isoformat() if self.exit_time else None,
            "status": self.status.value,
            "pnl": self.pnl,
            "pnl_percent": self.pnl_percent
        }

class TradeLogger:
    """Manages simulated trades and calculates performance metrics."""
    
    def __init__(self, live_mode: bool = False):
        self.live_mode = live_mode
        self.open_trades: Dict[int, SimulatedTrade] = {}
        self.trade_counter = 0
    
    async def place_order(self, symbol: str, side: TradeSide, quantity: int, 
                         price: float, order_type: str = "market") -> Dict[str, Any]:
        """Place a simulated order."""
        self.trade_counter += 1
        trade_id = self.trade_counter
        
        # Create simulated trade
        trade = SimulatedTrade(symbol, side, quantity, price)
        trade.id = trade_id
        self.open_trades[trade_id] = trade
        
        # Log the trade
        await self._log_trade_created(trade)
        
        # In live mode, this would call the actual broker
        if self.live_mode:
            # TODO: Implement actual broker integration
            await log_event("live_order_placed", {
                "trade_id": trade_id,
                "symbol": symbol,
                "side": side.value,
                "quantity": quantity,
                "price": price,
                "order_type": order_type
            })
        else:
            await log_event("sim_order_placed", {
                "trade_id": trade_id,
                "symbol": symbol,
                "side": side.value,
                "quantity": quantity,
                "price": price,
                "order_type": order_type
            })
        
        return {
            "trade_id": trade_id,
            "status": "filled",
            "filled_price": price,
            "filled_quantity": quantity
        }
    
    async def close_trade(self, trade_id: int, exit_price: float) -> Dict[str, Any]:
        """Close a simulated trade."""
        if trade_id not in self.open_trades:
            raise ValueError(f"Trade {trade_id} not found or already closed")
        
        trade = self.open_trades[trade_id]
        trade.close(exit_price)
        
        # Remove from open trades
        del self.open_trades[trade_id]
        
        # Log the trade closure
        await self._log_trade_closed(trade)
        
        return trade.to_dict()
    
    async def get_open_trades(self) -> List[Dict[str, Any]]:
        """Get all open trades."""
        return [trade.to_dict() for trade in self.open_trades.values()]
    
    async def get_closed_trades(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent closed trades from database."""
        conn = await get_db()
        cursor = await conn.execute("""
            SELECT * FROM sim_trades 
            WHERE status = 'closed' 
            ORDER BY exit_time DESC 
            LIMIT ?
        """, (limit,))
        rows = await cursor.fetchall()
        
        # Convert to list of dicts
        trades = []
        for row in rows:
            trade_dict = {
                "id": row[0],
                "symbol": row[1],
                "side": row[2],
                "quantity": row[3],
                "entry_price": row[4],
                "exit_price": row[5],
                "entry_time": row[6],
                "exit_time": row[7],
                "status": row[8],
                "pnl": row[9],
                "pnl_percent": row[10]
            }
            trades.append(trade_dict)
        
        return trades
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Calculate performance metrics from closed trades."""
        conn = await get_db()
        cursor = await conn.execute("""
            SELECT 
                COUNT(*) as total_trades,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losing_trades,
                SUM(pnl) as total_pnl,
                AVG(pnl) as avg_pnl,
                AVG(pnl_percent) as avg_pnl_percent,
                MAX(pnl) as max_win,
                MIN(pnl) as max_loss
            FROM sim_trades 
            WHERE status = 'closed'
        """)
        row = await cursor.fetchone()
        
        if not row or row[0] == 0:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "avg_pnl": 0.0,
                "avg_pnl_percent": 0.0,
                "max_win": 0.0,
                "max_loss": 0.0
            }
        
        total_trades = row[0]
        winning_trades = row[1]
        losing_trades = row[2]
        total_pnl = row[3] or 0.0
        avg_pnl = row[4] or 0.0
        avg_pnl_percent = row[5] or 0.0
        max_win = row[6] or 0.0
        max_loss = row[7] or 0.0
        
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0.0
        
        return {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": round(win_rate, 2),
            "total_pnl": round(total_pnl, 2),
            "avg_pnl": round(avg_pnl, 2),
            "avg_pnl_percent": round(avg_pnl_percent, 2),
            "max_win": round(max_win, 2),
            "max_loss": round(max_loss, 2)
        }
    
    async def _log_trade_created(self, trade: SimulatedTrade):
        """Log trade creation to database."""
        conn = await get_db()
        await conn.execute("""
            INSERT INTO sim_trades 
            (symbol, side, quantity, entry_price, entry_time, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            trade.symbol,
            trade.side.value,
            trade.quantity,
            trade.entry_price,
            trade.entry_time.isoformat(),
            trade.status.value
        ))
        
        # Get the inserted ID
        cursor = await conn.execute("SELECT last_insert_rowid()")
        trade.id = (await cursor.fetchone())[0]
        
        await log_event("trade_created", trade.to_dict())
    
    async def _log_trade_closed(self, trade: SimulatedTrade):
        """Log trade closure to database."""
        conn = await get_db()
        await conn.execute("""
            UPDATE sim_trades 
            SET exit_price = ?, exit_time = ?, status = ?, pnl = ?, pnl_percent = ?
            WHERE id = ?
        """, (
            trade.exit_price,
            trade.exit_time.isoformat(),
            trade.status.value,
            trade.pnl,
            trade.pnl_percent,
            trade.id
        ))
        
        await log_event("trade_closed", trade.to_dict())

# Global trade logger instance
trade_logger = TradeLogger(live_mode=False) 