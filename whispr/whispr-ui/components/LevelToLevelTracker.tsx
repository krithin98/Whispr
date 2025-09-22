import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { TrendingUp, TrendingDown, Activity, Target } from 'lucide-react';

interface LevelMove {
  from_level: string;
  to_level: string;
  direction: 'up' | 'down';
  timestamp: string;
  price_at_move: number;
  move_size: number;
}

interface LevelStats {
  total_moves: number;
  bullish_moves: number;
  bearish_moves: number;
  most_common_move: string;
  recent_moves: LevelMove[];
}

export const LevelToLevelTracker: React.FC<{ currentPrice: number; pdc: number; atrLevels: any }> = ({
  currentPrice,
  pdc,
  atrLevels,
}) => {
  const [levelStats, setLevelStats] = useState<LevelStats>({
    total_moves: 0,
    bullish_moves: 0,
    bearish_moves: 0,
    most_common_move: '',
    recent_moves: [],
  });

  const [currentLevel, setCurrentLevel] = useState<string>('');
  const [lastLevel, setLastLevel] = useState<string>('');

  // Define levels with their values
  const levels = [
    { name: 'Upper 61.8%', value: atrLevels.upper_0618, color: 'text-green-600' },
    { name: 'Upper 38.2%', value: atrLevels.upper_0382, color: 'text-green-500' },
    { name: 'Call Trigger', value: atrLevels.call_trigger, color: 'text-green-400' },
    { name: 'PDC', value: pdc, color: 'text-purple-500' },
    { name: 'Put Trigger', value: atrLevels.put_trigger, color: 'text-orange-400' },
    { name: 'Lower 38.2%', value: atrLevels.lower_0382, color: 'text-red-500' },
    { name: 'Lower 61.8%', value: atrLevels.lower_0618, color: 'text-red-600' },
  ];

  // Determine current level
  useEffect(() => {
    let current = 'Below Lower 61.8%';

    if (currentPrice >= atrLevels.upper_0618) {
      current = 'Above Upper 61.8%';
    } else if (currentPrice >= atrLevels.upper_0382) {
      current = 'Upper 38.2% → Upper 61.8%';
    } else if (currentPrice >= atrLevels.call_trigger) {
      current = 'Call → Upper 38.2%';
    } else if (currentPrice >= pdc) {
      current = 'PDC → Call';
    } else if (currentPrice >= atrLevels.put_trigger) {
      current = 'Put → PDC';
    } else if (currentPrice >= atrLevels.lower_0382) {
      current = 'Lower 38.2% → Put';
    } else if (currentPrice >= atrLevels.lower_0618) {
      current = 'Lower 61.8% → Lower 38.2%';
    }

    if (current !== currentLevel && lastLevel !== '') {
      // We've moved levels!
      const move: LevelMove = {
        from_level: lastLevel,
        to_level: current,
        direction: currentPrice > pdc ? 'up' : 'down',
        timestamp: new Date().toISOString(),
        price_at_move: currentPrice,
        move_size: Math.abs(currentPrice - pdc),
      };

      setLevelStats(prev => ({
        total_moves: prev.total_moves + 1,
        bullish_moves: prev.bullish_moves + (move.direction === 'up' ? 1 : 0),
        bearish_moves: prev.bearish_moves + (move.direction === 'down' ? 1 : 0),
        most_common_move: prev.most_common_move, // Would need more logic to track this
        recent_moves: [move, ...prev.recent_moves].slice(0, 10),
      }));
    }

    setLastLevel(currentLevel);
    setCurrentLevel(current);
  }, [currentPrice, pdc, atrLevels, currentLevel, lastLevel]);

  // Mock data for demonstration - in production this would come from the API
  const todaysMoves = [
    { from: 'PDC', to: 'Put Trigger', time: '09:35 AM', price: 6595.71 },
    { from: 'Put Trigger', to: 'Lower 38.2%', time: '10:15 AM', price: 6588.87 },
    { from: 'Lower 38.2%', to: 'Put Trigger', time: '10:45 AM', price: 6595.71 },
    { from: 'Put Trigger', to: 'PDC', time: '11:30 AM', price: 6606.76 },
    { from: 'PDC', to: 'Put Trigger', time: '12:15 PM', price: 6595.71 },
    { from: 'Put Trigger', to: 'Lower 38.2%', time: '01:00 PM', price: 6588.87 },
  ];

  const getLevelColor = (level: string) => {
    if (level.includes('Upper') || level.includes('Call')) return 'text-green-500';
    if (level.includes('Lower') || level.includes('Put')) return 'text-red-500';
    if (level.includes('PDC')) return 'text-purple-500';
    return 'text-gray-500';
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <Activity className="w-5 h-5" />
          Level-to-Level Movement Tracker
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Current Status */}
        <div className="p-3 bg-secondary rounded-lg">
          <div className="text-sm text-muted-foreground mb-1">Current Zone</div>
          <div className={`text-lg font-semibold ${getLevelColor(currentLevel)}`}>
            {currentLevel}
          </div>
          <div className="text-sm mt-1">
            Price: ${currentPrice.toFixed(2)}
          </div>
        </div>

        {/* Today's Statistics */}
        <div>
          <div className="text-sm font-medium mb-2">Today's Level Movements</div>
          <div className="grid grid-cols-3 gap-2 text-sm">
            <div className="bg-secondary/50 p-2 rounded">
              <div className="text-muted-foreground">Total</div>
              <div className="font-bold text-lg">{todaysMoves.length}</div>
            </div>
            <div className="bg-green-500/10 p-2 rounded">
              <div className="text-muted-foreground">Bullish</div>
              <div className="font-bold text-lg text-green-500">3</div>
            </div>
            <div className="bg-red-500/10 p-2 rounded">
              <div className="text-muted-foreground">Bearish</div>
              <div className="font-bold text-lg text-red-500">3</div>
            </div>
          </div>
        </div>

        {/* Recent Movements */}
        <div>
          <div className="text-sm font-medium mb-2">Recent Level-to-Level Moves</div>
          <div className="space-y-1 max-h-48 overflow-y-auto">
            {todaysMoves.map((move, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-2 bg-secondary/30 rounded text-xs"
              >
                <div className="flex items-center gap-2">
                  {move.to > move.from ? (
                    <TrendingUp className="w-3 h-3 text-green-500" />
                  ) : (
                    <TrendingDown className="w-3 h-3 text-red-500" />
                  )}
                  <span className={getLevelColor(move.from)}>{move.from}</span>
                  <span className="text-muted-foreground">→</span>
                  <span className={getLevelColor(move.to)}>{move.to}</span>
                </div>
                <div className="text-muted-foreground">
                  {move.time}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Key Levels Quick Reference */}
        <div className="border-t pt-3">
          <div className="text-xs text-muted-foreground mb-2">Distance to Key Levels</div>
          <div className="space-y-1 text-xs">
            {levels.map((level) => {
              const distance = level.value - currentPrice;
              const isNear = Math.abs(distance) < 2;
              return (
                <div
                  key={level.name}
                  className={`flex justify-between ${isNear ? 'font-bold' : ''}`}
                >
                  <span className={level.color}>{level.name}:</span>
                  <span className={`font-mono ${distance > 0 ? 'text-green-500' : 'text-red-500'}`}>
                    {distance > 0 ? '+' : ''}{distance.toFixed(2)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Common Patterns */}
        <div className="border-t pt-3">
          <div className="text-xs text-muted-foreground mb-2">Most Common Moves Today</div>
          <div className="space-y-1 text-xs">
            <div className="flex justify-between">
              <span>Put ↔ Lower 38.2%:</span>
              <span className="font-bold">3 times</span>
            </div>
            <div className="flex justify-between">
              <span>Put ↔ PDC:</span>
              <span className="font-bold">2 times</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};