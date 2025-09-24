// API service for Whispr Trading Copilot
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Yahoo Finance API for real-time data (fallback)
const YAHOO_FINANCE_API = 'https://query1.finance.yahoo.com/v8/finance/chart';

export interface Strategy {
  id: number;
  name: string;
  description?: string;
  strategy_type?: string;
  conditions?: string;
  strategy_expression?: string;
  prompt_tpl?: string;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface Trade {
  id: number;
  symbol: string;
  side: 'buy' | 'sell';
  quantity: number;
  entry_price: number;
  exit_price?: number;
  pnl?: number;
  status: 'open' | 'closed';
  created_at: string;
  closed_at?: string;
}

export interface StrategyTrigger {
  id: number;
  strategy_id: number;
  strategy_name: string;
  symbol: string;
  timeframe: string;
  trigger_type: string;
  side: 'buy' | 'sell';
  trigger_price: number;
  trigger_time: string;
  outcome?: string;
  outcome_price?: number;
  outcome_time?: string;
}

export interface LivePrice {
  timestamp: string;
  symbol: string;
  price: number;
  volume: number;
  bid: number;
  ask: number;
  change: number;
  change_percent: number;
  tick_id: number;
  source: string;
}

export interface PerformanceMetrics {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  total_pnl: number;
  average_pnl: number;
  largest_win: number;
  largest_loss: number;
}

export interface HistoricalData {
  data: Array<{
    date: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
  }>;
}

export interface TriggersSummary {
  total_triggers: number;
  successful_triggers: number;
  success_rate: number;
  average_profit: number;
  strategy_breakdown: Array<{
    strategy_name: string;
    trigger_count: number;
    success_rate: number;
  }>;
}

export interface CostComparison {
  current_costs: {
    groq_tokens: number;
    groq_cost: number;
    openai_tokens: number;
    openai_cost: number;
  };
  projected_savings: number;
  efficiency_score: number;
}

// Yahoo Finance API Functions (Updated to use backend yfinance)
export const yahooFinance = {
  async getQuote(symbol: string): Promise<LivePrice> {
    try {
      // Use our backend endpoint for SPY data
      if (symbol.toUpperCase() === 'SPY') {
        const response = await fetch(`${API_BASE_URL}/market-data/spy`);
        if (!response.ok) throw new Error('Failed to fetch SPY data from backend');
        
        const result = await response.json();
        const data = result.data;
        
        return {
          timestamp: data.timestamp,
          symbol: data.symbol,
          price: data.price,
          volume: data.volume,
          bid: data.bid,
          ask: data.ask,
          change: data.change,
          change_percent: data.change_percent,
          tick_id: data.tick_id,
          source: data.source
        };
      } else {
        // Fallback to original Yahoo Finance API for other symbols
        const response = await fetch(`${YAHOO_FINANCE_API}/${symbol}?interval=1m&range=1d`);
        if (!response.ok) throw new Error('Failed to fetch quote');
        
        const data = await response.json();
        const quote = data.chart.result[0];
        const meta = quote.meta;
        const indicators = quote.indicators.quote[0];
        
        const currentPrice = meta.regularMarketPrice;
        const previousClose = meta.previousClose;
        const change = currentPrice - previousClose;
        const changePercent = (change / previousClose) * 100;
        
        return {
          timestamp: new Date().toISOString(),
          symbol: symbol.toUpperCase(),
          price: currentPrice,
          volume: indicators.volume?.[indicators.volume.length - 1] || 0,
          bid: currentPrice - 0.01, // Approximate bid
          ask: currentPrice + 0.01, // Approximate ask
          change: change,
          change_percent: changePercent,
          tick_id: Date.now(),
          source: 'Yahoo Finance'
        };
      }
    } catch (error) {
      console.error('Failed to fetch market data:', error);
      // Fallback to realistic simulated data
      const basePrice = 450 + Math.random() * 20; // SPY-like price range
      const change = (Math.random() - 0.5) * 5;
      const changePercent = (change / basePrice) * 100;
      
      return {
        timestamp: new Date().toISOString(),
        symbol: symbol.toUpperCase(),
        price: basePrice,
        volume: 50000000 + Math.random() * 20000000, // Realistic volume
        bid: basePrice - 0.01,
        ask: basePrice + 0.01,
        change: change,
        change_percent: changePercent,
        tick_id: Date.now(),
        source: 'Simulated (Rate Limited)'
      };
    }
  },

  async getMultipleQuotes(symbols: string[]): Promise<LivePrice[]> {
    const quotes = await Promise.all(
      symbols.map(symbol => this.getQuote(symbol))
    );
    return quotes;
  },

  async getHistoricalData(symbol: string, startDate: string, endDate: string, interval: string = "1d"): Promise<HistoricalData> {
    try {
      const response = await fetch(
        `${API_BASE_URL}/market-data/historical/${symbol}?start_date=${startDate}&end_date=${endDate}&interval=${interval}`
      );
      
      if (!response.ok) throw new Error('Failed to fetch historical data');
      
      const result = await response.json();
      return result;
    } catch (error) {
      console.error('Failed to fetch historical data:', error);
      throw error;
    }
  }
};

// API Functions
export const api = {
  // Strategy Management
  async getStrategies(): Promise<Strategy[]> {
    const response = await fetch(`${API_BASE_URL}/strategies`);
    if (!response.ok) throw new Error('Failed to fetch strategies');
    return response.json();
  },

  async createStrategy(strategy: Omit<Strategy, 'id' | 'created_at' | 'updated_at'>): Promise<Strategy> {
    const response = await fetch(`${API_BASE_URL}/strategies`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(strategy),
    });
    if (!response.ok) throw new Error('Failed to create strategy');
    return response.json();
  },

  async updateStrategy(id: number, strategy: Partial<Strategy>): Promise<Strategy> {
    const response = await fetch(`${API_BASE_URL}/strategies/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(strategy),
    });
    if (!response.ok) throw new Error('Failed to update strategy');
    return response.json();
  },

  async deleteStrategy(id: number): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/strategies/${id}`, {
      method: 'DELETE',
    });
    if (!response.ok) throw new Error('Failed to delete strategy');
  },

  async toggleStrategy(id: number): Promise<Strategy> {
    const response = await fetch(`${API_BASE_URL}/strategies/${id}/toggle`, {
      method: 'POST',
    });
    if (!response.ok) throw new Error('Failed to toggle strategy');
    return response.json();
  },

  // Trade Management
  async getOpenTrades(): Promise<Trade[]> {
    const response = await fetch(`${API_BASE_URL}/trades/open`);
    if (!response.ok) throw new Error('Failed to fetch open trades');
    return response.json();
  },

  async getClosedTrades(limit: number = 100): Promise<Trade[]> {
    const response = await fetch(`${API_BASE_URL}/trades/closed?limit=${limit}`);
    if (!response.ok) throw new Error('Failed to fetch closed trades');
    return response.json();
  },

  async placeTrade(trade: {
    symbol: string;
    side: 'buy' | 'sell';
    quantity: number;
    price: number;
    order_type?: string;
  }): Promise<Trade> {
    const response = await fetch(`${API_BASE_URL}/trades`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(trade),
    });
    if (!response.ok) throw new Error('Failed to place trade');
    return response.json();
  },

  async closeTrade(tradeId: number, exitPrice: number): Promise<Trade> {
    const response = await fetch(`${API_BASE_URL}/trades/${tradeId}/close`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ exit_price: exitPrice }),
    });
    if (!response.ok) throw new Error('Failed to close trade');
    return response.json();
  },

  async getPerformance(): Promise<PerformanceMetrics> {
    const response = await fetch(`${API_BASE_URL}/trades/performance`);
    if (!response.ok) throw new Error('Failed to fetch performance');
    return response.json();
  },

  // Strategy Triggers
  async getStrategyTriggers(params?: {
    strategy_id?: number;
    strategy_name?: string;
    symbol?: string;
    timeframe?: string;
    trigger_type?: string;
    side?: string;
    start_date?: string;
    end_date?: string;
    limit?: number;
  }): Promise<StrategyTrigger[]> {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) searchParams.append(key, value.toString());
      });
    }
    
    const response = await fetch(`${API_BASE_URL}/strategy-triggers?${searchParams}`);
    if (!response.ok) throw new Error('Failed to fetch strategy triggers');
    return response.json();
  },

  async updateTriggerOutcome(
    triggerId: number,
    outcome: string,
    outcomePrice?: number,
    outcomeTime?: string
  ): Promise<StrategyTrigger> {
    const response = await fetch(`${API_BASE_URL}/strategy-triggers/${triggerId}/outcome`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        outcome,
        outcome_price: outcomePrice,
        outcome_time: outcomeTime,
      }),
    });
    if (!response.ok) throw new Error('Failed to update trigger outcome');
    return response.json();
  },

  // Analytics
  async getStrategyTriggersSummary(): Promise<TriggersSummary> {
    const response = await fetch(`${API_BASE_URL}/strategy-triggers/analytics/summary`);
    if (!response.ok) throw new Error('Failed to fetch triggers summary');
    return response.json();
  },

  // WebSocket connection for real-time data
  createWebSocketConnection(): WebSocket {
    return new WebSocket(`ws://localhost:8000/ws/ticks`);
  },

  // Cost comparison
  async getCostComparison(): Promise<CostComparison> {
    const response = await fetch(`${API_BASE_URL}/costs`);
    if (!response.ok) throw new Error('Failed to fetch cost comparison');
    return response.json();
  },

  // Yahoo Finance integration
  yahooFinance,
};

// Utility functions
export const formatCurrency = (amount: number): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(amount);
};

export const formatPercentage = (value: number): string => {
  return `${value > 0 ? '+' : ''}${value.toFixed(2)}%`;
};

export const formatDateTime = (dateString: string): string => {
  return new Date(dateString).toLocaleString('en-US', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
};

export const getStatusColor = (status: string): string => {
  switch (status.toLowerCase()) {
    case 'active':
    case 'open':
      return 'text-green-400';
    case 'closed':
      return 'text-blue-400';
    case 'inactive':
      return 'text-gray-400';
    default:
      return 'text-white';
  }
};

export const getSideColor = (side: string): string => {
  switch (side.toLowerCase()) {
    case 'buy':
      return 'text-blue-400';
    case 'sell':
      return 'text-red-400';
    default:
      return 'text-white';
  }
};

// Backtesting API endpoints
export const backtestingApi = {
  // Get available strategies for backtesting
  getStrategies: async () => {
    const response = await fetch(`${API_BASE_URL}/backtest/strategies`);
    if (!response.ok) {
      throw new Error('Failed to fetch strategies');
    }
    return response.json();
  },

  // Run backtest for a single strategy
  backtestStrategy: async (strategyId: number, symbol: string = 'SPY', startDate?: string, endDate?: string) => {
    const response = await fetch(`${API_BASE_URL}/backtest/strategy`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        strategy_id: strategyId,
        symbol,
        start_date: startDate,
        end_date: endDate,
      }),
    });
    if (!response.ok) {
      throw new Error('Backtest failed');
    }
    return response.json();
  },

  // Run backtest for multiple strategies
  backtestMultiple: async (strategyIds: number[], symbol: string = 'SPY', startDate?: string, endDate?: string) => {
    const response = await fetch(`${API_BASE_URL}/backtest/multiple`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        strategy_ids: strategyIds,
        symbol,
        start_date: startDate,
        end_date: endDate,
      }),
    });
    if (!response.ok) {
      throw new Error('Multiple backtest failed');
    }
    return response.json();
  },
}; 