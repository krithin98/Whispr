import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { TrendingUp, TrendingDown, Target, AlertCircle } from 'lucide-react';
import { ATRLevels } from '@/lib/api';

interface LevelTrackerProps {
  currentPrice: number;
  pdc: number;
  atrLevels: ATRLevels;
}

export const LevelTracker: React.FC<LevelTrackerProps> = ({
  currentPrice,
  pdc,
  atrLevels,
}) => {
  // Calculate distances to key levels
  const distanceToPut = currentPrice - atrLevels.put_trigger;
  const distanceToCall = atrLevels.call_trigger - currentPrice;
  const distanceTo382Below = currentPrice - atrLevels.lower_0382;
  const distanceTo382Above = atrLevels.upper_0382 - currentPrice;
  const distanceTo618Below = currentPrice - atrLevels.lower_0618;
  const distanceTo618Above = atrLevels.upper_0618 - currentPrice;

  // Check if we're at or near a key level (within $2)
  const isNearPutTrigger = Math.abs(distanceToPut) < 2;
  const isNearCallTrigger = Math.abs(distanceToCall) < 2;
  const isNear382Below = Math.abs(distanceTo382Below) < 2;
  const isNear382Above = Math.abs(distanceTo382Above) < 2;

  // Determine current zone
  const getCurrentZone = () => {
    if (currentPrice >= atrLevels.upper_0618) return { zone: 'Extended Call', color: 'text-green-600' };
    if (currentPrice >= atrLevels.upper_0382) return { zone: 'Golden Gate Long (38.2% → 61.8%)', color: 'text-green-500' };
    if (currentPrice >= atrLevels.call_trigger) return { zone: 'Call Trigger Zone', color: 'text-green-400' };
    if (currentPrice >= pdc) return { zone: 'Above PDC', color: 'text-blue-400' };
    if (currentPrice >= atrLevels.put_trigger) return { zone: 'Neutral Zone', color: 'text-gray-400' };
    if (currentPrice >= atrLevels.lower_0382) return { zone: 'Put Trigger Zone', color: 'text-orange-400' };
    if (currentPrice >= atrLevels.lower_0618) return { zone: 'Golden Gate Short (38.2% → 61.8%)', color: 'text-red-500' };
    return { zone: 'Extended Put', color: 'text-red-600' };
  };

  const currentZone = getCurrentZone();

  // Calculate next targets based on current position
  const getNextTargets = () => {
    const targets = [];

    // If we're at PUT trigger, next targets are:
    if (isNearPutTrigger) {
      targets.push(
        { name: '38.2% Below (Golden Gate Entry)', price: atrLevels.lower_0382, distance: distanceTo382Below, direction: 'down' },
        { name: 'PDC (Recovery)', price: pdc, distance: pdc - currentPrice, direction: 'up' }
      );
    }
    // If we're at CALL trigger, next targets are:
    else if (isNearCallTrigger) {
      targets.push(
        { name: '38.2% Above (Golden Gate Entry)', price: atrLevels.upper_0382, distance: distanceTo382Above, direction: 'up' },
        { name: 'PDC (Pullback)', price: pdc, distance: currentPrice - pdc, direction: 'down' }
      );
    }
    // If in Golden Gate zone
    else if (currentPrice >= atrLevels.lower_0382 && currentPrice <= atrLevels.lower_0618) {
      targets.push(
        { name: '61.8% Target (Golden Gate Complete)', price: atrLevels.lower_0618, distance: distanceTo618Below, direction: 'down' },
        { name: 'Put Trigger (Exit)', price: atrLevels.put_trigger, distance: atrLevels.put_trigger - currentPrice, direction: 'up' }
      );
    }

    return targets;
  };

  const nextTargets = getNextTargets();

  return (
    <Card className={`${isNearPutTrigger || isNearCallTrigger ? 'border-2 border-yellow-500' : ''}`}>
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <Target className="w-5 h-5" />
          Level-to-Level Tracker
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Current Status */}
        <div className="p-3 bg-secondary rounded-lg">
          <div className="text-sm text-muted-foreground mb-1">Current Zone</div>
          <div className={`text-lg font-semibold ${currentZone.color}`}>
            {currentZone.zone}
          </div>
          <div className="text-sm mt-2">
            Price: ${currentPrice.toFixed(2)} | PDC: ${pdc.toFixed(2)}
          </div>
        </div>

        {/* Alert if at trigger */}
        {(isNearPutTrigger || isNearCallTrigger) && (
          <div className="p-3 bg-yellow-500/10 border border-yellow-500/50 rounded-lg animate-pulse">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-yellow-500" />
              <div>
                <div className="font-semibold text-yellow-500">
                  {isNearPutTrigger ? '🎯 AT PUT TRIGGER!' : '🎯 AT CALL TRIGGER!'}
                </div>
                <div className="text-xs text-muted-foreground mt-1">
                  Watch for level-to-level movement
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Next Targets */}
        <div>
          <div className="text-sm font-medium mb-2">Next Level Targets</div>
          <div className="space-y-2">
            {nextTargets.map((target, idx) => (
              <div key={idx} className="flex items-center justify-between p-2 bg-secondary/50 rounded">
                <div className="flex items-center gap-2">
                  {target.direction === 'up' ? (
                    <TrendingUp className="w-4 h-4 text-green-500" />
                  ) : (
                    <TrendingDown className="w-4 h-4 text-red-500" />
                  )}
                  <div>
                    <div className="text-sm font-medium">{target.name}</div>
                    <div className="text-xs text-muted-foreground">
                      ${target.price.toFixed(2)}
                    </div>
                  </div>
                </div>
                <div className={`text-sm font-mono ${target.direction === 'up' ? 'text-green-500' : 'text-red-500'}`}>
                  {target.direction === 'up' ? '+' : ''}{target.distance.toFixed(2)}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Quick Level Reference */}
        <div className="border-t pt-3">
          <div className="text-xs text-muted-foreground mb-2">Key Levels</div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="flex justify-between">
              <span>Call Trigger:</span>
              <span className={`font-mono ${isNearCallTrigger ? 'text-yellow-500 font-bold' : ''}`}>
                ${atrLevels.call_trigger.toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between">
              <span>Put Trigger:</span>
              <span className={`font-mono ${isNearPutTrigger ? 'text-yellow-500 font-bold' : ''}`}>
                ${atrLevels.put_trigger.toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between">
              <span>Upper 38.2%:</span>
              <span className="font-mono">${atrLevels.upper_0382.toFixed(2)}</span>
            </div>
            <div className="flex justify-between">
              <span>Lower 38.2%:</span>
              <span className={`font-mono ${isNear382Below ? 'text-yellow-500' : ''}`}>
                ${atrLevels.lower_0382.toFixed(2)}
              </span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};