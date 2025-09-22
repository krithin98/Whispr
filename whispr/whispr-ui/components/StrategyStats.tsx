import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { TrendingUp, TrendingDown, Activity, Target } from 'lucide-react';
import { DailyStats } from '@/lib/api';

interface StrategyStatsProps {
  stats: DailyStats;
  currentPrice: number;
  atr: number;
}

export const StrategyStats: React.FC<StrategyStatsProps> = ({
  stats,
  currentPrice,
  atr,
}) => {
  const volatility = ((atr / currentPrice) * 100).toFixed(2);

  const statCards = [
    {
      title: 'Current Price',
      value: `$${currentPrice.toFixed(2)}`,
      subtitle: `ATR: $${atr.toFixed(2)}`,
      icon: Activity,
      color: 'text-blue-500',
    },
    {
      title: 'Daily P&L',
      value: `$${stats.daily_pnl.toFixed(2)}`,
      subtitle: `${stats.daily_pnl >= 0 ? '+' : ''}${((stats.daily_pnl / 10000) * 100).toFixed(1)}%`,
      icon: stats.daily_pnl >= 0 ? TrendingUp : TrendingDown,
      color: stats.daily_pnl >= 0 ? 'text-green-500' : 'text-red-500',
    },
    {
      title: 'Hit Rate',
      value: `${(stats.hit_rate || 0).toFixed(1)}%`,
      subtitle: `${stats.total_triggers || 0} triggers today`,
      icon: Target,
      color: 'text-purple-500',
    },
    {
      title: 'Volatility',
      value: `${volatility}%`,
      subtitle: 'Daily ATR %',
      icon: Activity,
      color: 'text-yellow-500',
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {statCards.map((stat, index) => (
        <Card key={index}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{stat.title}</CardTitle>
            <stat.icon className={`h-4 w-4 ${stat.color}`} />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${stat.color}`}>{stat.value}</div>
            <p className="text-xs text-muted-foreground">{stat.subtitle}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
};

export const StrategyBreakdown: React.FC<{ stats: DailyStats }> = ({ stats }) => {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Strategy Performance</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <span className="text-sm text-muted-foreground">Golden Gate Triggers</span>
            <span className="font-medium">{stats.gg_triggers || 0}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-sm text-muted-foreground">VOMY Triggers</span>
            <span className="font-medium">{stats.vomy_triggers || 0}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-sm text-muted-foreground">Avg Time to Target</span>
            <span className="font-medium">{(stats.avg_time_to_target || 0).toFixed(1)} min</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-sm text-muted-foreground">Total Triggers</span>
            <span className="font-medium">{stats.total_triggers || 0}</span>
          </div>
        </div>

        {/* Performance Bar */}
        <div className="mt-6">
          <div className="flex justify-between text-xs text-muted-foreground mb-1">
            <span>Win Rate</span>
            <span>{(stats.hit_rate || 0).toFixed(1)}%</span>
          </div>
          <div className="w-full bg-secondary rounded-full h-2">
            <div
              className="bg-green-500 h-2 rounded-full transition-all"
              style={{ width: `${stats.hit_rate || 0}%` }}
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
};