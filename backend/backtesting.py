import asyncio
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import pandas as pd
import numpy as np
from database import get_db, log_event

@dataclass
class BacktestResult:
    strategy_id: int
    strategy_name: str
    symbol: str
    start_date: str
    end_date: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_return: float
    total_pnl: float
    max_drawdown: float
    sharpe_ratio: float
    avg_trade_duration: float
    profit_factor: float
    trades: List[Dict[str, Any]]
    equity_curve: List[Dict[str, Any]]

class BacktestingEngine:
    def __init__(self):
        self.risk_per_trade = 0.02  # 2% risk per trade
        self.initial_capital = 100000  # $100k starting capital
        
    async def get_historical_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Generate simulated historical price data for backtesting."""
        await log_event("backtest_info", {
            "message": f"Generating simulated historical data for {symbol} from {start_date} to {end_date}",
            "symbol": symbol,
            "start_date": start_date,
            "end_date": end_date
        })
        
        # Generate simulated data since we're using Schwab only
        return await self._generate_simulated_data(start_date, end_date)
    
    async def _generate_simulated_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Generate realistic simulated data as fallback."""
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        # Generate daily OHLCV data
        dates = pd.date_range(start=start, end=end, freq='D')
        base_price = 450  # SPY-like starting price
        
        data = []
        current_price = base_price
        
        for date in dates:
            # Skip weekends
            if date.weekday() >= 5:
                continue
                
            # Generate realistic price movement
            daily_return = np.random.normal(0.0005, 0.015)  # 0.05% daily return, 1.5% volatility
            current_price *= (1 + daily_return)
            
            # Generate OHLCV
            high = current_price * (1 + abs(np.random.normal(0, 0.005)))
            low = current_price * (1 - abs(np.random.normal(0, 0.005)))
            open_price = current_price * (1 + np.random.normal(0, 0.002))
            volume = int(np.random.normal(50000000, 10000000))
            
            data.append({
                'date': date.strftime('%Y-%m-%d'),
                'open': round(open_price, 2),
                'high': round(high, 2),
                'low': round(low, 2),
                'close': round(current_price, 2),
                'volume': max(volume, 1000000)
            })
        
        await log_event("backtest_info", {
            "message": f"Generated {len(data)} days of simulated data",
            "data_points": len(data)
        })
        
        return pd.DataFrame(data)
    
    async def calculate_position_size(self, entry_price: float, stop_loss: float, capital: float) -> int:
        """Calculate position size based on risk management rules."""
        risk_amount = capital * self.risk_per_trade
        price_risk = abs(entry_price - stop_loss)
        if price_risk == 0:
            return 0
        return int(risk_amount / price_risk)
    
    async def backtest_strategy(self, strategy_id: int, symbol: str, start_date: str, end_date: str) -> BacktestResult:
        """Run backtest for a specific strategy."""
        try:
            # Get strategy details
            conn = await get_db()
            cursor = await conn.execute(
                "SELECT name, strategy_expression, strategy_type FROM strategies WHERE id = ?",
                (strategy_id,)
            )
            strategy = await cursor.fetchone()
            if not strategy:
                raise ValueError(f"Strategy {strategy_id} not found")
            
            strategy_name, strategy_expression, strategy_type = strategy
            
            # Get historical data
            historical_data = await self.get_historical_data(symbol, start_date, end_date)
            
            # Initialize backtest variables
            capital = self.initial_capital
            max_capital = capital
            trades = []
            equity_curve = []
            open_position = None
            
            # Track performance metrics
            total_trades = 0
            winning_trades = 0
            losing_trades = 0
            total_pnl = 0
            
            # Run backtest
            for i, row in historical_data.iterrows():
                current_price = row['close']
                current_date = row['date']
                
                # Update equity curve
                equity_curve.append({
                    'date': current_date,
                    'equity': capital,
                    'drawdown': (max_capital - capital) / max_capital if max_capital > 0 else 0
                })
                
                # Check if we have an open position
                if open_position:
                    # Check exit conditions
                    exit_price = None
                    exit_reason = None
                    
                    # Simple exit: 2% stop loss or 4% take profit
                    if current_price <= open_position['stop_loss']:
                        exit_price = open_position['stop_loss']
                        exit_reason = 'stop_loss'
                    elif current_price >= open_position['take_profit']:
                        exit_price = open_position['take_profit']
                        exit_reason = 'take_profit'
                    elif i == len(historical_data) - 1:  # Last day
                        exit_price = current_price
                        exit_reason = 'end_of_period'
                    
                    if exit_price:
                        # Close position
                        pnl = (exit_price - open_position['entry_price']) * open_position['quantity']
                        if open_position['side'] == 'sell':
                            pnl = -pnl
                        
                        capital += pnl
                        total_pnl += pnl
                        total_trades += 1
                        
                        if pnl > 0:
                            winning_trades += 1
                        
                        trade_duration = (datetime.strptime(current_date, "%Y-%m-%d") - 
                                        datetime.strptime(open_position['entry_date'], "%Y-%m-%d")).days
                        
                        trades.append({
                            'entry_date': open_position['entry_date'],
                            'exit_date': current_date,
                            'side': open_position['side'],
                            'entry_price': open_position['entry_price'],
                            'exit_price': exit_price,
                            'quantity': open_position['quantity'],
                            'pnl': pnl,
                            'duration_days': trade_duration,
                            'exit_reason': exit_reason
                        })
                        
                        open_position = None
                        max_capital = max(max_capital, capital)
                
                # Check for new entry signals
                if not open_position:
                    # Simple strategy logic based on strategy type
                    should_enter = False
                    entry_side = 'buy'
                    
                    if strategy_type == 'atr_based':
                        # ATR-based strategy: enter on price momentum
                        if i > 0:
                            prev_price = historical_data.iloc[i-1]['close']
                            momentum = (current_price - prev_price) / prev_price
                            should_enter = abs(momentum) > 0.01  # 1% momentum
                            entry_side = 'buy' if momentum > 0 else 'sell'
                    
                    elif strategy_type == 'vomy_ivomy':
                        # Volume-based strategy
                        avg_volume = historical_data['volume'].rolling(20).mean().iloc[i]
                        should_enter = row['volume'] > avg_volume * 1.5  # 50% above average
                        entry_side = 'buy' if current_price > historical_data.iloc[i-1]['close'] else 'sell'
                    
                    elif strategy_type == 'golden_gate':
                        # Golden Gate strategy: enter on specific price levels
                        if i > 0:
                            prev_close = historical_data.iloc[i-1]['close']
                            price_change = (current_price - prev_close) / prev_close
                            should_enter = abs(price_change) > 0.02  # 2% move
                            entry_side = 'buy' if price_change > 0 else 'sell'
                    
                    else:  # Standard strategy
                        # Use strategy expression if available
                        if strategy_expression and strategy_expression != 'True':
                            try:
                                # Simple expression evaluation
                                should_enter = eval(strategy_expression, {
                                    'price': current_price,
                                    'volume': row['volume'],
                                    'open': row['open'],
                                    'high': row['high'],
                                    'low': row['low'],
                                    'close': current_price
                                })
                            except:
                                should_enter = False
                        else:
                            # Default: enter randomly with 5% probability
                            should_enter = np.random.random() < 0.05
                            entry_side = 'buy' if np.random.random() < 0.6 else 'sell'
                    
                    if should_enter:
                        # Calculate position size
                        stop_loss = current_price * 0.98 if entry_side == 'buy' else current_price * 1.02
                        take_profit = current_price * 1.04 if entry_side == 'buy' else current_price * 0.96
                        
                        quantity = await self.calculate_position_size(current_price, stop_loss, capital)
                        
                        if quantity > 0:
                            open_position = {
                                'entry_date': current_date,
                                'entry_price': current_price,
                                'side': entry_side,
                                'quantity': quantity,
                                'stop_loss': stop_loss,
                                'take_profit': take_profit
                            }
            
            # Calculate final metrics
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            total_return = ((capital - self.initial_capital) / self.initial_capital * 100)
            
            # Calculate max drawdown
            max_drawdown = 0
            peak = self.initial_capital
            for point in equity_curve:
                if point['equity'] > peak:
                    peak = point['equity']
                drawdown = (peak - point['equity']) / peak
                max_drawdown = max(max_drawdown, drawdown)
            
            # Calculate Sharpe ratio (simplified)
            returns = []
            for i in range(1, len(equity_curve)):
                daily_return = (equity_curve[i]['equity'] - equity_curve[i-1]['equity']) / equity_curve[i-1]['equity']
                returns.append(daily_return)
            
            sharpe_ratio = 0
            if returns:
                avg_return = np.mean(returns)
                std_return = np.std(returns)
                if std_return > 0:
                    sharpe_ratio = avg_return / std_return * np.sqrt(252)  # Annualized
            
            # Calculate average trade duration
            avg_duration = 0
            if trades:
                durations = [trade['duration_days'] for trade in trades]
                avg_duration = np.mean(durations)
            
            # Calculate profit factor
            gross_profit = sum([trade['pnl'] for trade in trades if trade['pnl'] > 0])
            gross_loss = abs(sum([trade['pnl'] for trade in trades if trade['pnl'] < 0]))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            
            return BacktestResult(
                strategy_id=strategy_id,
                strategy_name=strategy_name,
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                total_trades=total_trades,
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                win_rate=win_rate,
                total_return=total_return,
                total_pnl=total_pnl,
                max_drawdown=max_drawdown * 100,  # Convert to percentage
                sharpe_ratio=sharpe_ratio,
                avg_trade_duration=avg_duration,
                profit_factor=profit_factor,
                trades=trades,
                equity_curve=equity_curve
            )
            
        except Exception as e:
            await log_event("backtest_error", {"error": f"Backtest failed for strategy {strategy_id}: {str(e)}"})
            raise
    
    async def backtest_multiple_strategies(self, strategy_ids: List[int], symbol: str, start_date: str, end_date: str) -> List[BacktestResult]:
        """Run backtests for multiple strategies."""
        results = []
        for strategy_id in strategy_ids:
            try:
                result = await self.backtest_strategy(strategy_id, symbol, start_date, end_date)
                results.append(result)
            except Exception as e:
                await log_event("backtest_error", {"error": f"Failed to backtest strategy {strategy_id}: {str(e)}"})
                continue
        return results

# Global instance
backtesting_engine = BacktestingEngine() 