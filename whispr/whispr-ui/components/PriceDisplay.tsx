import React from 'react';

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

interface PriceDisplayProps {
  data: PriceData | null;
}

export default function PriceDisplay({ data }: PriceDisplayProps) {
  if (!data) {
    return (
      <div className="bg-gray-900 rounded-lg p-6 animate-pulse">
        <div className="h-8 bg-gray-800 rounded w-32 mb-2"></div>
        <div className="h-4 bg-gray-800 rounded w-24"></div>
      </div>
    );
  }

  const priceChange = data.price - 6664.36; // PDC
  const priceChangePercent = (priceChange / 6664.36) * 100;
  const isPositive = priceChange >= 0;

  return (
    <div className="bg-gray-900 rounded-lg p-6 border border-gray-800">
      <div className="flex items-baseline justify-between mb-4">
        <div>
          <h2 className="text-sm font-medium text-gray-400 mb-1">S&P 500</h2>
          <div className="flex items-baseline gap-3">
            <span className="text-3xl font-bold text-white">
              ${data.price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
            <span className={`text-lg font-medium ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
              {isPositive ? '+' : ''}{priceChange.toFixed(2)}
            </span>
            <span className={`text-sm ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
              ({isPositive ? '+' : ''}{priceChangePercent.toFixed(2)}%)
            </span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4 text-sm">
        <div>
          <span className="text-gray-500">High</span>
          <div className="text-white font-medium">${data.high.toFixed(2)}</div>
        </div>
        <div>
          <span className="text-gray-500">Low</span>
          <div className="text-white font-medium">${data.low.toFixed(2)}</div>
        </div>
        <div>
          <span className="text-gray-500">Volume</span>
          <div className="text-white font-medium">
            {(data.volume / 1e9).toFixed(2)}B
          </div>
        </div>
      </div>

      {data.daily_stats && (
        <div className="mt-4 pt-4 border-t border-gray-800">
          <div className="flex justify-between text-xs text-gray-500">
            <span>Ticks: {data.daily_stats.tick_count}</span>
            <span>Day Range: ${data.daily_stats.daily_low?.toFixed(2)} - ${data.daily_stats.daily_high?.toFixed(2)}</span>
          </div>
        </div>
      )}
    </div>
  );
}