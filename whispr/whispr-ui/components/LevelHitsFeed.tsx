import React from 'react';
import { ArrowUpIcon, ArrowDownIcon } from 'lucide-react';

interface LevelHit {
  hit_time: string;
  timeframe: string;
  level_name: string;
  level_value: number;
  hit_price: number;
  direction: string;
  fib_ratio: number;
}

interface LevelHitsFeedProps {
  hits: LevelHit[];
}

export default function LevelHitsFeed({ hits }: LevelHitsFeedProps) {
  return (
    <div className="bg-gray-900 rounded-lg p-6 border border-gray-800">
      <h3 className="text-lg font-semibold text-white mb-4">Recent Level Hits</h3>

      <div className="space-y-2 max-h-96 overflow-y-auto">
        {hits.length === 0 ? (
          <div className="text-gray-500 text-center py-8">
            No level hits recorded today
          </div>
        ) : (
          hits.map((hit, index) => {
            const time = new Date(hit.hit_time).toLocaleTimeString('en-US', {
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit'
            });

            const isUp = hit.direction === 'up';

            return (
              <div
                key={`${hit.hit_time}-${index}`}
                className="flex items-center justify-between p-3 rounded bg-gray-800 hover:bg-gray-700 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className={`p-1 rounded ${isUp ? 'bg-green-900' : 'bg-red-900'}`}>
                    {isUp ? (
                      <ArrowUpIcon className="w-4 h-4 text-green-400" />
                    ) : (
                      <ArrowDownIcon className="w-4 h-4 text-red-400" />
                    )}
                  </div>

                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-white font-medium">{hit.level_name}</span>
                      <span className="text-xs text-gray-500">[{hit.timeframe}]</span>
                    </div>
                    <div className="text-xs text-gray-400">
                      ${hit.level_value.toFixed(2)} @ ${hit.hit_price.toFixed(2)}
                    </div>
                  </div>
                </div>

                <div className="text-right">
                  <div className="text-xs text-gray-400">{time}</div>
                  <div className={`text-xs ${isUp ? 'text-green-400' : 'text-red-400'}`}>
                    {hit.fib_ratio > 0 ? '+' : ''}{(hit.fib_ratio * 100).toFixed(1)}%
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}