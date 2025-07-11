import { useState, useEffect, useCallback, useRef } from 'react';
import { api, Strategy, Trade, StrategyTrigger, LivePrice, PerformanceMetrics } from '../api';

export interface WhisprDataState {
  // Live data
  livePrice: LivePrice | null;
  isConnected: boolean;
  
  // Strategies
  strategies: Strategy[];
  strategiesLoading: boolean;
  strategiesError: string | null;
  
  // Trades
  openTrades: Trade[];
  closedTrades: Trade[];
  tradesLoading: boolean;
  tradesError: string | null;
  
  // Performance
  performance: PerformanceMetrics | null;
  performanceLoading: boolean;
  performanceError: string | null;
  
  // Strategy triggers
  recentTriggers: StrategyTrigger[];
  triggersLoading: boolean;
  triggersError: string | null;
}

export interface WhisprDataActions {
  // Strategy actions
  refreshStrategies: () => Promise<void>;
  createStrategy: (strategy: Omit<Strategy, 'id' | 'created_at' | 'updated_at'>) => Promise<void>;
  updateStrategy: (id: number, strategy: Partial<Strategy>) => Promise<void>;
  deleteStrategy: (id: number) => Promise<void>;
  toggleStrategy: (id: number) => Promise<void>;
  
  // Trade actions
  refreshTrades: () => Promise<void>;
  placeTrade: (trade: { symbol: string; side: 'buy' | 'sell'; quantity: number; price: number; order_type?: string }) => Promise<void>;
  closeTrade: (tradeId: number, exitPrice: number) => Promise<void>;
  
  // Performance actions
  refreshPerformance: () => Promise<void>;
  
  // Trigger actions
  refreshTriggers: () => Promise<void>;
  updateTriggerOutcome: (triggerId: number, outcome: string, outcomePrice?: number, outcomeTime?: string) => Promise<void>;
}

export function useWhisprData(): WhisprDataState & WhisprDataActions {
  // State
  const [livePrice, setLivePrice] = useState<LivePrice | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [strategiesLoading, setStrategiesLoading] = useState(true);
  const [strategiesError, setStrategiesError] = useState<string | null>(null);
  
  const [openTrades, setOpenTrades] = useState<Trade[]>([]);
  const [closedTrades, setClosedTrades] = useState<Trade[]>([]);
  const [tradesLoading, setTradesLoading] = useState(true);
  const [tradesError, setTradesError] = useState<string | null>(null);
  
  const [performance, setPerformance] = useState<PerformanceMetrics | null>(null);
  const [performanceLoading, setPerformanceLoading] = useState(true);
  const [performanceError, setPerformanceError] = useState<string | null>(null);
  
  const [recentTriggers, setRecentTriggers] = useState<StrategyTrigger[]>([]);
  const [triggersLoading, setTriggersLoading] = useState(true);
  const [triggersError, setTriggersError] = useState<string | null>(null);
  
  // Refs for cleanup
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const priceUpdateIntervalRef = useRef<NodeJS.Timeout | null>(null);
  
  // Default symbol for live price
  const DEFAULT_SYMBOL = 'SPY';
  
  // Fetch live price from Yahoo Finance
  const fetchLivePrice = useCallback(async () => {
    try {
      const price = await api.yahooFinance.getQuote(DEFAULT_SYMBOL);
      setLivePrice(price);
      setIsConnected(true);
    } catch (error) {
      console.error('Failed to fetch live price:', error);
      setIsConnected(false);
    }
  }, []);
  
  // WebSocket connection
  const connectWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    
    try {
      const ws = api.createWebSocketConnection();
      wsRef.current = ws;
      
      ws.onopen = () => {
        setIsConnected(true);
        console.log('WebSocket connected');
      };
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          // Handle different message types
          if (data.timestamp && data.price) {
            // Live price update from WebSocket (if available)
            setLivePrice(data);
          } else if (data.type === 'suggestion') {
            // Strategy trigger/suggestion
            console.log('Strategy suggestion received:', data);
            // Refresh triggers to show new suggestion
            refreshTriggers();
          }
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };
      
      ws.onclose = () => {
        console.log('WebSocket disconnected');
        
        // Attempt to reconnect after 5 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          connectWebSocket();
        }, 5000);
      };
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
      
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
    }
  }, []);
  
  // API functions
  const refreshStrategies = useCallback(async () => {
    try {
      setStrategiesLoading(true);
      setStrategiesError(null);
      // Fetch real strategies from backend
      const data = await api.getStrategies();
      let strategies: Strategy[] = [];
      if (Array.isArray(data)) {
        strategies = data;
      } else if (data && typeof data === 'object' && 'strategies' in data) {
        const wrappedData = data as { strategies: Strategy[] };
        if (Array.isArray(wrappedData.strategies)) {
          strategies = wrappedData.strategies;
        }
      }
      setStrategies(strategies);
    } catch (error) {
      setStrategiesError(error instanceof Error ? error.message : 'Failed to fetch strategies');
    } finally {
      setStrategiesLoading(false);
    }
  }, []);
  
  const createStrategy = useCallback(async (strategy: Omit<Strategy, 'id' | 'created_at' | 'updated_at'>) => {
    try {
      await api.createStrategy(strategy);
      await refreshStrategies();
    } catch (error) {
      throw error;
    }
  }, [refreshStrategies]);
  
  const updateStrategy = useCallback(async (id: number, strategy: Partial<Strategy>) => {
    try {
      await api.updateStrategy(id, strategy);
      await refreshStrategies();
    } catch (error) {
      throw error;
    }
  }, [refreshStrategies]);
  
  const deleteStrategy = useCallback(async (id: number) => {
    try {
      await api.deleteStrategy(id);
      await refreshStrategies();
    } catch (error) {
      throw error;
    }
  }, [refreshStrategies]);
  
  const toggleStrategy = useCallback(async (id: number) => {
    try {
      await api.toggleStrategy(id);
      await refreshStrategies();
    } catch (error) {
      throw error;
    }
  }, [refreshStrategies]);
  
  const refreshTrades = useCallback(async () => {
    try {
      setTradesLoading(true);
      setTradesError(null);
      const [open, closed] = await Promise.all([
        api.getOpenTrades(),
        api.getClosedTrades(50) // Get last 50 closed trades
      ]);
      setOpenTrades(open);
      setClosedTrades(closed);
    } catch (error) {
      setTradesError(error instanceof Error ? error.message : 'Failed to fetch trades');
    } finally {
      setTradesLoading(false);
    }
  }, []);
  
  const refreshPerformance = useCallback(async () => {
    try {
      setPerformanceLoading(true);
      setPerformanceError(null);
      const data = await api.getPerformance();
      setPerformance(data);
    } catch (error) {
      setPerformanceError(error instanceof Error ? error.message : 'Failed to fetch performance');
    } finally {
      setPerformanceLoading(false);
    }
  }, []);
  
  const placeTrade = useCallback(async (trade: { symbol: string; side: 'buy' | 'sell'; quantity: number; price: number; order_type?: string }) => {
    try {
      await api.placeTrade(trade);
      await refreshTrades();
      await refreshPerformance();
    } catch (error) {
      throw error;
    }
  }, [refreshTrades, refreshPerformance]);
  
  const closeTrade = useCallback(async (tradeId: number, exitPrice: number) => {
    try {
      await api.closeTrade(tradeId, exitPrice);
      await refreshTrades();
      await refreshPerformance();
    } catch (error) {
      throw error;
    }
  }, [refreshTrades, refreshPerformance]);
  
  const refreshTriggers = useCallback(async () => {
    try {
      setTriggersLoading(true);
      setTriggersError(null);
      const data = await api.getStrategyTriggers({ limit: 20 }); // Get last 20 triggers
      setRecentTriggers(Array.isArray(data) ? data : []);
    } catch (error) {
      setTriggersError(error instanceof Error ? error.message : 'Failed to fetch triggers');
    } finally {
      setTriggersLoading(false);
    }
  }, []);
  
  const updateTriggerOutcome = useCallback(async (triggerId: number, outcome: string, outcomePrice?: number, outcomeTime?: string) => {
    try {
      await api.updateTriggerOutcome(triggerId, outcome, outcomePrice, outcomeTime);
      await refreshTriggers();
    } catch (error) {
      throw error;
    }
  }, [refreshTriggers]);
  
  // Initial data load
  useEffect(() => {
    const loadInitialData = async () => {
      await Promise.all([
        refreshStrategies(),
        refreshTrades(),
        refreshPerformance(),
        refreshTriggers(),
        fetchLivePrice() // Initial price fetch
      ]);
    };
    
    loadInitialData();
  }, [refreshStrategies, refreshTrades, refreshPerformance, refreshTriggers, fetchLivePrice]);
  
  // WebSocket connection
  useEffect(() => {
    connectWebSocket();
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [connectWebSocket]);
  
  // Set up periodic price updates from yfinance (via backend)
  useEffect(() => {
    // Update price every 15 seconds for more responsive data
    priceUpdateIntervalRef.current = setInterval(() => {
      fetchLivePrice();
    }, 15000);
    
    return () => {
      if (priceUpdateIntervalRef.current) {
        clearInterval(priceUpdateIntervalRef.current);
      }
    };
  }, [fetchLivePrice]);
  
  return {
    // State
    livePrice,
    isConnected,
    strategies,
    strategiesLoading,
    strategiesError,
    openTrades,
    closedTrades,
    tradesLoading,
    tradesError,
    performance,
    performanceLoading,
    performanceError,
    recentTriggers,
    triggersLoading,
    triggersError,
    
    // Actions
    refreshStrategies,
    createStrategy,
    updateStrategy,
    deleteStrategy,
    toggleStrategy,
    refreshTrades,
    placeTrade,
    closeTrade,
    refreshPerformance,
    refreshTriggers,
    updateTriggerOutcome,
  };
} 