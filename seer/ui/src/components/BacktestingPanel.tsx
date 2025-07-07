'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, TrendingUp, TrendingDown, Target, BarChart3, Calendar, DollarSign } from 'lucide-react';

interface Strategy {
  id: number;
  name: string;
  type: string;
  description: string;
}

interface BacktestResult {
  strategy_id: number;
  strategy_name: string;
  symbol: string;
  start_date: string;
  end_date: string;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  total_return: number;
  total_pnl: number;
  max_drawdown: number;
  sharpe_ratio: number;
  avg_trade_duration: number;
  profit_factor: number;
  trades: Array<{
    entry_date: string;
    exit_date: string;
    side: string;
    entry_price: number;
    exit_price: number;
    quantity: number;
    pnl: number;
    duration_days: number;
    exit_reason: string;
  }>;
  equity_curve: Array<{
    date: string;
    equity: number;
    drawdown: number;
  }>;
}

interface BacktestSummary {
  total_strategies: number;
  avg_return: number;
  avg_win_rate: number;
  best_strategy: BacktestResult | null;
  worst_strategy: BacktestResult | null;
}

export default function BacktestingPanel() {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [selectedStrategies, setSelectedStrategies] = useState<number[]>([]);
  const [symbol, setSymbol] = useState('SPY');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [backtestResults, setBacktestResults] = useState<BacktestResult[]>([]);
  const [backtestSummary, setBacktestSummary] = useState<BacktestSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Set default dates (90 days ago to today)
  useEffect(() => {
    const today = new Date();
    const ninetyDaysAgo = new Date(today.getTime() - 90 * 24 * 60 * 60 * 1000);
    
    setEndDate(today.toISOString().split('T')[0]);
    setStartDate(ninetyDaysAgo.toISOString().split('T')[0]);
  }, []);

  // Load available strategies
  useEffect(() => {
    fetchStrategies();
  }, []);

  const fetchStrategies = async () => {
    try {
      const response = await fetch('/api/backtest/strategies');
      if (response.ok) {
        const data = await response.json();
        setStrategies(data.strategies || []);
      } else {
        setError('Failed to load strategies');
      }
    } catch (err) {
      setError('Failed to load strategies');
    }
  };

  const runBacktest = async () => {
    if (selectedStrategies.length === 0) {
      setError('Please select at least one strategy');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/backtest/multiple', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          strategy_ids: selectedStrategies,
          symbol,
          start_date: startDate,
          end_date: endDate,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setBacktestResults(data.results || []);
        setBacktestSummary(data.summary || null);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Backtest failed');
      }
    } catch (err) {
      setError('Backtest failed');
    } finally {
      setIsLoading(false);
    }
  };

  const toggleStrategy = (strategyId: number) => {
    setSelectedStrategies(prev => 
      prev.includes(strategyId) 
        ? prev.filter(id => id !== strategyId)
        : [...prev, strategyId]
    );
  };

  const selectAllStrategies = () => {
    setSelectedStrategies(strategies.map(s => s.id));
  };

  const clearSelection = () => {
    setSelectedStrategies([]);
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(value);
  };

  const formatPercentage = (value: number) => {
    return `${value.toFixed(2)}%`;
  };

  const getPerformanceColor = (value: number) => {
    return value >= 0 ? 'text-green-600' : 'text-red-600';
  };

  const getPerformanceIcon = (value: number) => {
    return value >= 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />;
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5" />
            Strategy Backtesting
          </CardTitle>
          <CardDescription>
            Test your trading strategies against historical data to evaluate performance
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Strategy Selection */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <Label className="text-base font-semibold">Select Strategies</Label>
              <div className="space-x-2">
                <Button variant="outline" size="sm" onClick={selectAllStrategies}>
                  Select All
                </Button>
                <Button variant="outline" size="sm" onClick={clearSelection}>
                  Clear
                </Button>
              </div>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 max-h-60 overflow-y-auto">
              {strategies.map((strategy) => (
                <div
                  key={strategy.id}
                  className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                    selectedStrategies.includes(strategy.id)
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                  onClick={() => toggleStrategy(strategy.id)}
                >
                  <div className="flex items-start gap-3">
                    <Checkbox
                      checked={selectedStrategies.includes(strategy.id)}
                      onChange={() => toggleStrategy(strategy.id)}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-sm truncate">{strategy.name}</div>
                      <div className="text-xs text-gray-500 mt-1">{strategy.type}</div>
                      <div className="text-xs text-gray-600 mt-1 line-clamp-2">
                        {strategy.description}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Backtest Parameters */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="symbol">Symbol</Label>
              <Input
                id="symbol"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                placeholder="SPY"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="startDate">Start Date</Label>
              <Input
                id="startDate"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="endDate">End Date</Label>
              <Input
                id="endDate"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
            </div>
          </div>

          {/* Run Backtest Button */}
          <Button
            onClick={runBacktest}
            disabled={isLoading || selectedStrategies.length === 0}
            className="w-full"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Running Backtest...
              </>
            ) : (
              <>
                <BarChart3 className="w-4 h-4 mr-2" />
                Run Backtest
              </>
            )}
          </Button>

          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Backtest Results */}
      {backtestResults.length > 0 && (
        <div className="space-y-6">
          {/* Summary Card */}
          {backtestSummary && (
            <Card>
              <CardHeader>
                <CardTitle>Backtest Summary</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold">{backtestSummary.total_strategies}</div>
                    <div className="text-sm text-gray-500">Strategies Tested</div>
                  </div>
                  <div className="text-center">
                    <div className={`text-2xl font-bold ${getPerformanceColor(backtestSummary.avg_return)}`}>
                      {formatPercentage(backtestSummary.avg_return)}
                    </div>
                    <div className="text-sm text-gray-500">Average Return</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold">{formatPercentage(backtestSummary.avg_win_rate)}</div>
                    <div className="text-sm text-gray-500">Average Win Rate</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold">
                      {backtestSummary.best_strategy ? formatPercentage(backtestSummary.best_strategy.total_return) : 'N/A'}
                    </div>
                    <div className="text-sm text-gray-500">Best Strategy</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Individual Strategy Results */}
          <Tabs defaultValue="overview" className="space-y-4">
            <TabsList>
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="trades">Trade Details</TabsTrigger>
              <TabsTrigger value="equity">Equity Curve</TabsTrigger>
            </TabsList>

            <TabsContent value="overview" className="space-y-4">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {backtestResults.map((result) => (
                  <Card key={result.strategy_id}>
                    <CardHeader>
                      <CardTitle className="flex items-center justify-between">
                        <span className="truncate">{result.strategy_name}</span>
                        <Badge variant={result.total_return >= 0 ? "default" : "destructive"}>
                          {formatPercentage(result.total_return)}
                        </Badge>
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      {/* Key Metrics */}
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <div className="text-sm text-gray-500">Total Trades</div>
                          <div className="text-lg font-semibold">{result.total_trades}</div>
                        </div>
                        <div>
                          <div className="text-sm text-gray-500">Win Rate</div>
                          <div className="text-lg font-semibold">{formatPercentage(result.win_rate)}</div>
                        </div>
                        <div>
                          <div className="text-sm text-gray-500">Total P&L</div>
                          <div className={`text-lg font-semibold ${getPerformanceColor(result.total_pnl)}`}>
                            {formatCurrency(result.total_pnl)}
                          </div>
                        </div>
                        <div>
                          <div className="text-sm text-gray-500">Max Drawdown</div>
                          <div className="text-lg font-semibold text-red-600">
                            {formatPercentage(result.max_drawdown)}
                          </div>
                        </div>
                      </div>

                      {/* Additional Metrics */}
                      <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span>Sharpe Ratio:</span>
                          <span>{result.sharpe_ratio.toFixed(2)}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span>Profit Factor:</span>
                          <span>{result.profit_factor.toFixed(2)}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span>Avg Trade Duration:</span>
                          <span>{result.avg_trade_duration.toFixed(1)} days</span>
                        </div>
                      </div>

                      {/* Win/Loss Breakdown */}
                      <div className="space-y-2">
                        <div className="text-sm font-medium">Trade Breakdown</div>
                        <div className="flex gap-2">
                          <div className="flex-1 bg-green-100 rounded p-2 text-center">
                            <div className="text-green-800 font-semibold">{result.winning_trades}</div>
                            <div className="text-green-600 text-xs">Wins</div>
                          </div>
                          <div className="flex-1 bg-red-100 rounded p-2 text-center">
                            <div className="text-red-800 font-semibold">{result.losing_trades}</div>
                            <div className="text-red-600 text-xs">Losses</div>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </TabsContent>

            <TabsContent value="trades" className="space-y-4">
              {backtestResults.map((result) => (
                <Card key={result.strategy_id}>
                  <CardHeader>
                    <CardTitle>{result.strategy_name} - Trade Details</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Entry Date</TableHead>
                          <TableHead>Exit Date</TableHead>
                          <TableHead>Side</TableHead>
                          <TableHead>Entry Price</TableHead>
                          <TableHead>Exit Price</TableHead>
                          <TableHead>Quantity</TableHead>
                          <TableHead>P&L</TableHead>
                          <TableHead>Duration</TableHead>
                          <TableHead>Exit Reason</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {result.trades.map((trade, index) => (
                          <TableRow key={index}>
                            <TableCell>{trade.entry_date}</TableCell>
                            <TableCell>{trade.exit_date}</TableCell>
                            <TableCell>
                              <Badge variant={trade.side === 'buy' ? 'default' : 'secondary'}>
                                {trade.side.toUpperCase()}
                              </Badge>
                            </TableCell>
                            <TableCell>{formatCurrency(trade.entry_price)}</TableCell>
                            <TableCell>{formatCurrency(trade.exit_price)}</TableCell>
                            <TableCell>{trade.quantity}</TableCell>
                            <TableCell className={getPerformanceColor(trade.pnl)}>
                              {formatCurrency(trade.pnl)}
                            </TableCell>
                            <TableCell>{trade.duration_days} days</TableCell>
                            <TableCell>
                              <Badge variant="outline" className="text-xs">
                                {trade.exit_reason.replace('_', ' ')}
                              </Badge>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </CardContent>
                </Card>
              ))}
            </TabsContent>

            <TabsContent value="equity" className="space-y-4">
              {backtestResults.map((result) => (
                <Card key={result.strategy_id}>
                  <CardHeader>
                    <CardTitle>{result.strategy_name} - Equity Curve</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {/* Simple equity curve visualization */}
                      <div className="h-64 bg-gray-50 rounded-lg p-4">
                        <div className="text-center text-gray-500">
                          Equity curve visualization would go here
                        </div>
                        <div className="text-sm text-gray-400 mt-2">
                          Showing {result.equity_curve.length} data points from {result.start_date} to {result.end_date}
                        </div>
                      </div>
                      
                      {/* Key equity metrics */}
                      <div className="grid grid-cols-3 gap-4">
                        <div className="text-center">
                          <div className="text-sm text-gray-500">Final Equity</div>
                          <div className="text-lg font-semibold">
                            {formatCurrency(result.equity_curve[result.equity_curve.length - 1]?.equity || 0)}
                          </div>
                        </div>
                        <div className="text-center">
                          <div className="text-sm text-gray-500">Peak Equity</div>
                          <div className="text-lg font-semibold">
                            {formatCurrency(Math.max(...result.equity_curve.map(p => p.equity)))}
                          </div>
                        </div>
                        <div className="text-center">
                          <div className="text-sm text-gray-500">Max Drawdown</div>
                          <div className="text-lg font-semibold text-red-600">
                            {formatPercentage(result.max_drawdown)}
                          </div>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </TabsContent>
          </Tabs>
        </div>
      )}
    </div>
  );
} 