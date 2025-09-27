// API client for Whispr backend
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

export interface PriceData {
  timestamp: string;
  price: number;
  high: number;
  low: number;
  volume: number;
}

export interface ATRLevels {
  atr: number;
  put_trigger: number;
  call_trigger: number;
  lower_0382: number;
  upper_0382: number;
  lower_0618: number;
  upper_0618: number;
}

export interface Trigger {
  id: number;
  timestamp: string;
  type: string;
  direction: string;
  price: number;
  target: number;
  stop_loss: number;
  status: string;
}

export interface Candle {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface MarketState {
  timestamp: string;
  current_price: number;
  atr: number;
  last_update: string;
}

export interface DailyStats {
  total_triggers: number;
  gg_triggers: number;
  vomy_triggers: number;
  daily_pnl: number;
  hit_rate: number;
  avg_time_to_target: number;
}

class WhisprAPI {
  private baseUrl: string;

  constructor() {
    this.baseUrl = API_BASE;
  }

  async getMarketState(): Promise<MarketState> {
    const response = await fetch(`${this.baseUrl}/api/market-state`);
    if (!response.ok) throw new Error('Failed to fetch market state');
    return response.json();
  }

  async getRecentCandles(timeframe: string = '10m', count: number = 100): Promise<Candle[]> {
    const response = await fetch(`${this.baseUrl}/api/recent-candles/${timeframe}?count=${count}`);
    if (!response.ok) throw new Error('Failed to fetch candles');
    return response.json();
  }

  async getRecentTriggers(hours: number = 24): Promise<Trigger[]> {
    const response = await fetch(`${this.baseUrl}/api/triggers/recent?hours=${hours}`);
    if (!response.ok) throw new Error('Failed to fetch triggers');
    return response.json();
  }

  async getDailyAnalytics(): Promise<DailyStats> {
    const response = await fetch(`${this.baseUrl}/api/analytics/daily`);
    if (!response.ok) throw new Error('Failed to fetch analytics');
    return response.json();
  }

  async getPnL(days: number = 7): Promise<any[]> {
    const response = await fetch(`${this.baseUrl}/api/analytics/pnl/${days}`);
    if (!response.ok) throw new Error('Failed to fetch P&L');
    return response.json();
  }

  async getActivePositions(): Promise<Trigger[]> {
    const response = await fetch(`${this.baseUrl}/api/positions/active`);
    if (!response.ok) throw new Error('Failed to fetch positions');
    return response.json();
  }

  async createManualTrigger(
    trigger_type: string,
    direction: string,
    price: number,
    target: number,
    stop_loss: number
  ): Promise<{ status: string; message: string }> {
    const response = await fetch(`${this.baseUrl}/api/trigger/manual`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ trigger_type, direction, price, target, stop_loss }),
    });
    if (!response.ok) throw new Error('Failed to create trigger');
    return response.json();
  }
}

export const whisprAPI = new WhisprAPI();