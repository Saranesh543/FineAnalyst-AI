import React from 'react';

export const COLORS = [
  '#22d3ee', // Cyan
  '#2dd4bf', // Teal
  '#6366f1', // Indigo
  '#a855f7', // Purple
  '#3b82f6', // Blue
  '#f43f5e', // Rose/Accent
  '#f59e0b', // Amber/Accent
  '#10b981'  // Emerald
];

export const formatNumber = (value: any, formatType?: string) => {
  if (value === null || value === undefined) return '-';
  const numValue = Number(value);
  if (isNaN(numValue)) return String(value);

  if (formatType === 'currency' || String(value).includes('$')) {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(numValue);
  }
  if (formatType === 'percentage' || String(value).includes('%')) {
    const pctVal = numValue > 1 ? numValue / 100 : numValue;
    return new Intl.NumberFormat('en-US', { style: 'percent', maximumFractionDigits: 1 }).format(pctVal);
  }
  if (formatType === 'compact' || numValue >= 10000) {
    return new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 }).format(numValue);
  }
  if (formatType === 'decimal') {
    return new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(numValue);
  }
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(numValue);
};

export const formatTick = (val: any) => {
  if (typeof val === 'string' && val.length > 15) {
    return val.substring(0, 15) + '...';
  }
  return formatNumber(val, 'compact');
};

export const ChartDefs = () => (
  <defs>
    <filter id="cyanGlow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="4" result="blur" />
      <feComposite in="SourceGraphic" in2="blur" operator="over" />
    </filter>
    <linearGradient id="cyanGradient" x1="0" y1="0" x2="0" y2="1">
      <stop offset="5%" stopColor="#22d3ee" stopOpacity={0.4}/>
      <stop offset="95%" stopColor="#22d3ee" stopOpacity={0}/>
    </linearGradient>
  </defs>
);

export const CustomTooltip = ({ active, payload, label, formatType }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-black/70 backdrop-blur-md border border-cyan-500/20 rounded-xl shadow-[0_0_20px_rgba(34,211,238,0.15)] p-4 text-sm z-50 relative text-foreground min-w-[150px]">
        <p className="font-bold text-foreground mb-2 border-b border-border/10 pb-2">{label}</p>
        <div className="space-y-2">
          {payload.map((entry: any, index: number) => (
            <div key={index} className="flex items-center justify-between space-x-6">
              <div className="flex items-center space-x-2">
                <div className="w-2.5 h-2.5 rounded-full shadow-[0_0_8px_rgba(34,211,238,0.5)]" style={{ backgroundColor: entry.color || COLORS[index % COLORS.length] }} />
                <span className="text-muted-foreground font-medium text-xs uppercase tracking-wider">{entry.name}:</span>
              </div>
              <span className="font-bold text-cyan-400">{formatNumber(entry.value, formatType)}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }
  return null;
};
