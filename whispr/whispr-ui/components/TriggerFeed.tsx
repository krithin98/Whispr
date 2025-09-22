import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowUpCircle, ArrowDownCircle, AlertCircle } from 'lucide-react';
import { Trigger } from '@/lib/api';

interface TriggerFeedProps {
  triggers: Trigger[];
}

export const TriggerFeed: React.FC<TriggerFeedProps> = ({ triggers }) => {
  const [animatedTriggers, setAnimatedTriggers] = useState<Set<number>>(new Set());

  useEffect(() => {
    // Animate new triggers
    const latestTrigger = triggers[0];
    if (latestTrigger && !animatedTriggers.has(latestTrigger.id)) {
      setAnimatedTriggers(prev => new Set(prev).add(latestTrigger.id));
    }
  }, [triggers]);

  const getTriggerIcon = (direction: string) => {
    switch (direction.toLowerCase()) {
      case 'long':
        return <ArrowUpCircle className="w-5 h-5 text-green-500" />;
      case 'short':
        return <ArrowDownCircle className="w-5 h-5 text-red-500" />;
      default:
        return <AlertCircle className="w-5 h-5 text-yellow-500" />;
    }
  };

  const getTriggerColor = (type: string) => {
    if (type.includes('Golden Gate')) return 'text-yellow-500';
    if (type.includes('VOMY')) return 'text-purple-500';
    if (type.includes('ATR')) return 'text-blue-500';
    return 'text-gray-500';
  };

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  return (
    <Card className="h-full overflow-hidden">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2">
          <AlertCircle className="w-5 h-5" />
          Live Triggers
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <div className="space-y-1 max-h-[600px] overflow-y-auto">
          {triggers.length === 0 ? (
            <div className="p-4 text-center text-muted-foreground">
              No triggers detected
            </div>
          ) : (
            triggers.slice(0, 20).map((trigger) => (
              <div
                key={trigger.id}
                className={`px-4 py-3 border-b hover:bg-secondary/50 transition-all ${
                  animatedTriggers.has(trigger.id) ? 'trigger-alert' : ''
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-2">
                    {getTriggerIcon(trigger.direction)}
                    <div>
                      <div className={`font-medium ${getTriggerColor(trigger.type)}`}>
                        {trigger.type}
                      </div>
                      <div className="text-sm text-muted-foreground">
                        {formatTime(trigger.timestamp)}
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-mono text-sm font-medium">
                      ${trigger.price.toFixed(2)}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      T: ${trigger.target.toFixed(2)}
                    </div>
                  </div>
                </div>
                <div className="mt-2 flex items-center justify-between text-xs">
                  <span className={`px-2 py-1 rounded-full ${
                    trigger.status === 'active'
                      ? 'bg-green-500/20 text-green-500'
                      : trigger.status === 'completed'
                      ? 'bg-blue-500/20 text-blue-500'
                      : 'bg-gray-500/20 text-gray-500'
                  }`}>
                    {trigger.status}
                  </span>
                  <span className="text-muted-foreground">
                    SL: ${trigger.stop_loss.toFixed(2)}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
};