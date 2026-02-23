'use client';

import { cn } from '@/lib/utils';
import { Card } from './Card';
import type { LucideIcon } from 'lucide-react';

interface DataStatProps {
  label: string;
  value: string;
  trend?: string;
  trendType?: 'positive' | 'negative' | 'neutral';
  icon?: LucideIcon;
  className?: string;
}

export default function DataStat({
  label,
  value,
  trend,
  trendType = 'neutral',
  icon: Icon,
  className,
}: DataStatProps) {
  return (
    <Card variant="default" className={cn('flex items-start gap-4', className)}>
      {Icon && (
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-emerald-500/20 text-emerald-400">
          <Icon className="h-5 w-5" />
        </div>
      )}
      <div className="space-y-2">
        <p className="text-sm text-gray-400">{label}</p>
        <p className="text-2xl font-mono text-primary">{value}</p>
        {trend && (
          <p
            className={cn(
              'text-xs font-medium',
              trendType === 'positive' && 'text-emerald-400',
              trendType === 'negative' && 'text-red-400',
              trendType === 'neutral' && 'text-data',
            )}
          >
            {trend}
          </p>
        )}
      </div>
    </Card>
  );
}

// Named export alias for backward compatibility
export { DataStat };
