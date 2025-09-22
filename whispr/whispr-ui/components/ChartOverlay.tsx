import React, { useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  ReferenceArea,
  Area,
  ComposedChart,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Candle, ATRLevels } from '@/lib/api';

interface ChartOverlayProps {
  candles: Candle[];
  currentPrice: number;
  pdc: number;
  atrLevels: ATRLevels;
  timezone?: 'EST' | 'CST' | 'PST';
}

export const ChartOverlay: React.FC<ChartOverlayProps> = ({
  candles,
  currentPrice,
  pdc,
  atrLevels,
  timezone = 'EST',
}) => {
  const formatTimeForTimezone = (timestamp: string) => {
    // Timestamps from API are in GMT/UTC without timezone marker
    // Append 'Z' to indicate UTC if not present
    const utcTimestamp = timestamp.includes('Z') || timestamp.includes('+')
      ? timestamp
      : timestamp.replace(' ', 'T') + 'Z';

    const date = new Date(utcTimestamp);
    const options: Intl.DateTimeFormatOptions = {
      hour: '2-digit',
      minute: '2-digit',
      timeZone: timezone === 'EST' ? 'America/New_York' :
                timezone === 'CST' ? 'America/Chicago' :
                'America/Los_Angeles'
    };
    return date.toLocaleTimeString('en-US', options);
  };

  const chartData = useMemo(() => {
    // Filter candles to only show from 9:30 AM EST onwards
    const filteredCandles = candles.filter(candle => {
      // Convert timestamp to UTC Date
      const utcTimestamp = candle.timestamp.includes('Z') || candle.timestamp.includes('+')
        ? candle.timestamp
        : candle.timestamp.replace(' ', 'T') + 'Z';

      const date = new Date(utcTimestamp);

      // Convert to EST to check the time
      const estTime = new Date(date.toLocaleString("en-US", {timeZone: "America/New_York"}));
      const hours = estTime.getHours();
      const minutes = estTime.getMinutes();
      const totalMinutes = hours * 60 + minutes;

      // 9:30 AM EST = 570 minutes from midnight
      // 4:00 PM EST = 960 minutes from midnight
      return totalMinutes >= 570 && totalMinutes <= 960;
    });

    return filteredCandles.map(candle => ({
      time: formatTimeForTimezone(candle.timestamp),
      open: candle.open,
      high: candle.high,
      low: candle.low,
      close: candle.close,
      volume: candle.volume,
    }));
  }, [candles, timezone]);

  const yDomain = useMemo(() => {
    if (candles.length === 0) return [currentPrice - 20, currentPrice + 20];

    // Get price range from candles
    const prices = candles.flatMap(c => [c.high, c.low]);

    // Include current price and PDC
    prices.push(currentPrice, pdc);

    // Include the trigger levels and 38.2% levels (most relevant for trading)
    // Don't include 61.8% levels as they're too far and compress the chart
    prices.push(
      atrLevels.put_trigger,
      atrLevels.call_trigger,
      atrLevels.lower_0382,
      atrLevels.upper_0382
    );

    const min = Math.min(...prices);
    const max = Math.max(...prices);

    // Add smaller padding for better scale
    const range = max - min;
    const padding = range * 0.05; // 5% padding instead of 10%

    return [min - padding, max + padding];
  }, [candles, atrLevels, currentPrice, pdc]);

  const formatPrice = (value: number) => `$${value.toFixed(2)}`;

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-background border rounded-lg p-2 shadow-lg">
          <p className="text-xs text-muted-foreground">{data.time}</p>
          <div className="space-y-1 mt-1">
            <p className="text-xs">
              <span className="text-muted-foreground">O:</span> {formatPrice(data.open)}
            </p>
            <p className="text-xs">
              <span className="text-muted-foreground">H:</span> {formatPrice(data.high)}
            </p>
            <p className="text-xs">
              <span className="text-muted-foreground">L:</span> {formatPrice(data.low)}
            </p>
            <p className="text-xs">
              <span className="text-muted-foreground">C:</span> {formatPrice(data.close)}
            </p>
          </div>
        </div>
      );
    }
    return null;
  };

  // Check if we're at a trigger level
  const isAtPutTrigger = Math.abs(currentPrice - atrLevels.put_trigger) < 2;
  const isAtCallTrigger = Math.abs(currentPrice - atrLevels.call_trigger) < 2;

  return (
    <Card className={`h-full ${isAtPutTrigger ? 'border-orange-500 border-2' : isAtCallTrigger ? 'border-green-500 border-2' : ''}`}>
      <CardHeader className="pb-3">
        <div className="flex justify-between items-center">
          <CardTitle className="text-lg">SPX Price Action ({timezone})</CardTitle>
          {(isAtPutTrigger || isAtCallTrigger) && (
            <div className={`px-3 py-1 rounded-full text-sm font-semibold animate-pulse ${
              isAtPutTrigger ? 'bg-orange-500/20 text-orange-500' : 'bg-green-500/20 text-green-500'
            }`}>
              {isAtPutTrigger ? '🎯 AT PUT TRIGGER' : '🎯 AT CALL TRIGGER'}
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={500}>
          <ComposedChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#333" />
            <XAxis
              dataKey="time"
              stroke="#888"
              fontSize={10}
              interval="preserveStartEnd"
            />
            <YAxis
              domain={yDomain}
              stroke="#888"
              fontSize={10}
              tickFormatter={formatPrice}
            />
            <Tooltip content={<CustomTooltip />} />

            {/* Price line */}
            <Line
              type="monotone"
              dataKey="close"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={false}
            />

            {/* Current price line */}
            <ReferenceLine
              y={currentPrice}
              stroke="#fff"
              strokeWidth={2}
              strokeDasharray="5 5"
              label={{
                value: `Current: ${formatPrice(currentPrice)}`,
                position: 'right',
                fill: '#fff',
                fontSize: 12,
              }}
            />

            {/* PDC line */}
            <ReferenceLine
              y={pdc}
              stroke="#9333ea"
              strokeWidth={2}
              label={{
                value: `PDC: ${formatPrice(pdc)}`,
                position: 'right',
                fill: '#9333ea',
                fontSize: 12,
              }}
            />

            {/* ATR Levels */}
            {/* Golden Gate Zone - 38.2% to 61.8% */}
            <ReferenceArea
              y1={atrLevels.lower_0382}
              y2={atrLevels.lower_0618}
              fill="#ef4444"
              fillOpacity={0.1}
            />
            <ReferenceArea
              y1={atrLevels.upper_0382}
              y2={atrLevels.upper_0618}
              fill="#10b981"
              fillOpacity={0.1}
            />

            {/* Trigger lines */}
            <ReferenceLine
              y={atrLevels.put_trigger}
              stroke="#f59e0b"
              strokeWidth={1}
              strokeDasharray="3 3"
              label={{
                value: `Put (PDC-23.6%) ${formatPrice(atrLevels.put_trigger)}`,
                position: 'left',
                fill: '#f59e0b',
                fontSize: 10,
              }}
            />
            <ReferenceLine
              y={atrLevels.call_trigger}
              stroke="#f59e0b"
              strokeWidth={1}
              strokeDasharray="3 3"
              label={{
                value: `Call (PDC+23.6%) ${formatPrice(atrLevels.call_trigger)}`,
                position: 'left',
                fill: '#f59e0b',
                fontSize: 10,
              }}
            />

            {/* Fibonacci levels */}
            <ReferenceLine
              y={atrLevels.lower_0382}
              stroke="#ef4444"
              strokeWidth={1}
              opacity={0.5}
            />
            <ReferenceLine
              y={atrLevels.lower_0618}
              stroke="#ef4444"
              strokeWidth={1}
              opacity={0.5}
            />
            <ReferenceLine
              y={atrLevels.upper_0382}
              stroke="#10b981"
              strokeWidth={1}
              opacity={0.5}
            />
            <ReferenceLine
              y={atrLevels.upper_0618}
              stroke="#10b981"
              strokeWidth={1}
              opacity={0.5}
            />
          </ComposedChart>
        </ResponsiveContainer>

        {/* Level Legend */}
        <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-green-500/20 rounded" />
            <span>Golden Gate Long Zone (38.2% → 61.8%)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-red-500/20 rounded" />
            <span>Golden Gate Short Zone (61.8% → 38.2%)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-yellow-500 rounded" />
            <span>Trigger Levels (±23.6%)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-white rounded" />
            <span>Current Price</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};