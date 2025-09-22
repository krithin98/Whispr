import React, { useState, useEffect, useCallback } from 'react';
import Head from 'next/head';
import PriceDisplay from '../components/PriceDisplay';
import LevelChart from '../components/LevelChart';
import LevelHitsFeed from '../components/LevelHitsFeed';
import { Activity, TrendingUp, Layers, BarChart3 } from 'lucide-react';

interface PriceData {
  price: number;
  high: number;
  low: number;
  volume: number;
  timestamp: string;
  daily_stats?: {
    tick_count: number;
    daily_low: number;
    daily_high: number;
  };
}

interface LevelData {
  timeframe: string;
  pdc: number;
  atr: number;
  levels: any;
  current_position: any;
}

interface SystemHealth {
  status: string;
  last_tick: string;
  age_seconds: number;
  message: string;
}

export default function Whispr() {
  const [priceData, setPriceData] = useState<PriceData | null>(null);
  const [levelData, setLevelData] = useState<LevelData | null>(null);
  const [levelHits, setLevelHits] = useState<any[]>([]);
  const [selectedTimeframe, setSelectedTimeframe] = useState('day');
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null);
  const [patterns, setPatterns] = useState<any[]>([]);
  const [movements, setMovements] = useState<any>({ transitions: [], active_chains: {} });

  const timeframes = [
    { value: 'day', label: 'Day' },           // 14-period daily ATR
    { value: 'multiday', label: 'Multiday' }, // 20-period weekly ATR
    { value: 'swing', label: 'Swing' },       // Monthly ATR
    { value: 'position', label: 'Position' }, // Quarterly ATR
    { value: 'longterm', label: 'Long Term' } // Yearly ATR
  ];

  // Fetch data
  const fetchData = useCallback(async () => {
    try {
      // Fetch price
      const priceRes = await fetch('http://localhost:8000/api/price/current');
      const priceJson = await priceRes.json();
      setPriceData(priceJson);

      // Fetch levels
      const levelsRes = await fetch(`http://localhost:8000/api/levels/${selectedTimeframe}`);
      const levelsJson = await levelsRes.json();
      setLevelData(levelsJson);

      // Fetch hits
      const hitsRes = await fetch('http://localhost:8000/api/level-hits');
      const hitsJson = await hitsRes.json();
      setLevelHits(hitsJson.hits || []);

      // Fetch patterns
      const patternsRes = await fetch('http://localhost:8000/api/patterns');
      const patternsJson = await patternsRes.json();
      setPatterns(patternsJson.patterns || []);

      // Fetch movements
      const movementsRes = await fetch('http://localhost:8000/api/movements');
      const movementsJson = await movementsRes.json();
      setMovements(movementsJson);

      // System health
      const healthRes = await fetch('http://localhost:8000/api/system/health');
      const healthJson = await healthRes.json();
      setSystemHealth(healthJson);
    } catch (error) {
      console.error('Error fetching data:', error);
    }
  }, [selectedTimeframe]);

  // Initial fetch and periodic refresh
  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, [fetchData]);

  const healthColor = systemHealth?.status === 'healthy' ? 'text-green-400' :
                      systemHealth?.status === 'delayed' ? 'text-yellow-400' : 'text-red-400';

  return (
    <div className="min-h-screen bg-black text-white">
      <Head>
        <title>Whispr - Professional SPX Level Analytics</title>
        <meta name="description" content="Comprehensive ATR level tracking and movement analytics" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      {/* Header */}
      <header className="bg-gray-900 border-b border-gray-800">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <Layers className="w-8 h-8 text-blue-500" />
                <h1 className="text-2xl font-bold">Whispr</h1>
              </div>
              <span className="text-sm text-gray-400">Comprehensive SPX Level Analytics</span>
            </div>

            <div className="flex items-center gap-6">
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4" />
                <span className={`text-sm ${healthColor}`}>
                  {systemHealth?.status || 'Unknown'}
                </span>
              </div>

              {systemHealth && (
                <span className="text-xs text-gray-500">
                  {systemHealth.message}
                </span>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-6">
        {/* Top Stats Row */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <PriceDisplay data={priceData} />

          {/* Quick Stats */}
          <div className="bg-gray-900 rounded-lg p-6 border border-gray-800">
            <div className="flex items-center gap-2 mb-3">
              <TrendingUp className="w-5 h-5 text-blue-500" />
              <h3 className="text-sm font-medium text-gray-400">Patterns Today</h3>
            </div>
            <div className="text-2xl font-bold">{patterns.length}</div>
            {patterns.length > 0 && (
              <div className="mt-2 text-xs text-gray-500">
                Latest: {patterns[0]?.pattern_type}
              </div>
            )}
          </div>

          <div className="bg-gray-900 rounded-lg p-6 border border-gray-800">
            <div className="flex items-center gap-2 mb-3">
              <BarChart3 className="w-5 h-5 text-green-500" />
              <h3 className="text-sm font-medium text-gray-400">Level Hits</h3>
            </div>
            <div className="text-2xl font-bold">{levelHits.length}</div>
            <div className="mt-2 text-xs text-gray-500">
              Across all timeframes
            </div>
          </div>

          <div className="bg-gray-900 rounded-lg p-6 border border-gray-800">
            <div className="flex items-center gap-2 mb-3">
              <Activity className="w-5 h-5 text-purple-500" />
              <h3 className="text-sm font-medium text-gray-400">Transitions</h3>
            </div>
            <div className="text-2xl font-bold">{movements.total_transitions || 0}</div>
            <div className="mt-2 text-xs text-gray-500">
              Level movements today
            </div>
          </div>
        </div>

        {/* Timeframe Selector */}
        <div className="mb-6">
          <div className="flex gap-2 bg-gray-900 p-2 rounded-lg border border-gray-800 inline-flex">
            {timeframes.map(tf => (
              <button
                key={tf.value}
                onClick={() => setSelectedTimeframe(tf.value)}
                className={`px-4 py-2 rounded transition-colors ${
                  selectedTimeframe === tf.value
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:text-white hover:bg-gray-800'
                }`}
              >
                {tf.label}
              </button>
            ))}
          </div>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Level Chart - Takes 2 columns */}
          <div className="lg:col-span-2">
            {levelData && priceData && (
              <LevelChart
                levels={levelData.levels}
                currentPrice={priceData.price}
                pdc={levelData.pdc}
                atr={levelData.atr}
                timeframe={selectedTimeframe}
              />
            )}

            {/* Movement Patterns */}
            <div className="mt-6 bg-gray-900 rounded-lg p-6 border border-gray-800">
              <h3 className="text-lg font-semibold text-white mb-4">Active Patterns</h3>
              <div className="space-y-2">
                {patterns.slice(0, 5).map((pattern, idx) => (
                  <div key={idx} className="flex justify-between items-center p-3 bg-gray-800 rounded">
                    <div>
                      <span className="text-white font-medium">{pattern.pattern_type}</span>
                      <span className="text-xs text-gray-500 ml-2">[{pattern.timeframe}]</span>
                    </div>
                    <div className="text-sm text-gray-400">
                      {pattern.from_level} → {pattern.to_level}
                    </div>
                  </div>
                ))}
                {patterns.length === 0 && (
                  <div className="text-gray-500 text-center py-4">
                    No patterns detected yet
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Right Column - Level Hits Feed */}
          <div>
            <LevelHitsFeed hits={levelHits} />

            {/* Top Transitions */}
            <div className="mt-6 bg-gray-900 rounded-lg p-6 border border-gray-800">
              <h3 className="text-lg font-semibold text-white mb-4">Top Transitions</h3>
              <div className="space-y-2">
                {movements.transitions?.slice(0, 5).map((trans: any, idx: number) => (
                  <div key={idx} className="text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-400">
                        {trans.from_level} → {trans.to_level}
                      </span>
                      <span className="text-white">{trans.count}x</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="mt-12 border-t border-gray-800 bg-gray-900">
        <div className="container mx-auto px-4 py-6">
          <div className="flex justify-between items-center">
            <div className="text-sm text-gray-400">
              © 2025 Whispr - Professional Trading Analytics
            </div>
            <div className="text-xs text-gray-500">
              Tracking {Object.keys(levelData?.levels || {}).length} levels across 8 timeframes
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}