import React, { useMemo } from 'react';

interface Level {
  name: string;
  value: number;
  fib_ratio: number;
  direction: string;
}

interface LevelChartProps {
  levels: { [key: string]: Level };
  currentPrice: number;
  pdc: number;
  atr: number;
  timeframe: string;
}

export default function LevelChart({ levels, currentPrice, pdc, atr, timeframe }: LevelChartProps) {
  const sortedLevels = useMemo(() => {
    return Object.values(levels)
      .filter(level => !level.name.includes('beyond'))
      .sort((a, b) => b.value - a.value);
  }, [levels]);

  const pricePosition = ((currentPrice - pdc) / atr) * 100; // Position as % of ATR

  return (
    <div className="bg-gray-900 rounded-lg p-6 border border-gray-800">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-white mb-2">
          ATR Levels - {timeframe}
        </h3>
        <div className="flex gap-6 text-sm text-gray-400">
          <span>PDC: ${pdc.toFixed(2)}</span>
          <span>ATR: ${atr.toFixed(2)}</span>
          <span>Position: {(pricePosition / 100).toFixed(3)} ATR</span>
        </div>
      </div>

      <div className="relative">
        <div className="space-y-1.5">
          {sortedLevels.map((level) => {
            const isCurrentNear = Math.abs(currentPrice - level.value) < 2;
            const isPDC = level.name === 'PDC';
            const isKeyLevel = Math.abs(level.fib_ratio) === 1.0 || Math.abs(level.fib_ratio) === 2.0;

            return (
              <div
                key={level.name}
                className={`
                  flex items-center justify-between p-2 rounded transition-all
                  ${isCurrentNear ? 'bg-blue-900/30 border border-blue-500' : ''}
                  ${isPDC ? 'bg-gray-800 border border-gray-600' : ''}
                  ${isKeyLevel && !isPDC ? 'bg-gray-800/50' : ''}
                  hover:bg-gray-800 cursor-pointer
                `}
              >
                <div className="flex items-center gap-3">
                  <div className={`w-2 h-2 rounded-full ${
                    level.direction === 'upper' ? 'bg-green-500' :
                    level.direction === 'lower' ? 'bg-red-500' :
                    'bg-blue-500'
                  }`} />
                  <span className={`font-medium ${
                    isPDC ? 'text-blue-400' : 'text-gray-300'
                  }`}>
                    {level.name}
                  </span>
                  <span className="text-xs text-gray-500">
                    ({level.fib_ratio > 0 ? '+' : ''}{(level.fib_ratio * 100).toFixed(1)}%)
                  </span>
                </div>

                <div className="flex items-center gap-3">
                  <span className="text-white font-mono">
                    ${level.value.toFixed(2)}
                  </span>
                  {currentPrice > level.value && (
                    <span className="text-xs text-green-400">✓</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Current Price Indicator */}
        <div className="absolute left-0 right-0 flex items-center pointer-events-none"
             style={{
               top: `${((sortedLevels[0].value - currentPrice) / (sortedLevels[0].value - sortedLevels[sortedLevels.length - 1].value)) * 100}%`
             }}>
          <div className="bg-yellow-500 h-0.5 flex-1"></div>
          <div className="bg-yellow-500 text-black text-xs font-bold px-2 py-1 rounded">
            ${currentPrice.toFixed(2)}
          </div>
          <div className="bg-yellow-500 h-0.5 flex-1"></div>
        </div>
      </div>
    </div>
  );
}