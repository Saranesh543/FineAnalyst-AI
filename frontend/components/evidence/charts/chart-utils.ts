import React from 'react';

export const COLORS = ['#2563eb', '#16a34a', '#dc2626', '#eab308', '#9333ea', '#0891b2', '#f97316', '#14b8a6'];

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

export const CustomTooltip = ({ active, payload, label, formatType }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-background border rounded-lg shadow-lg p-3 text-sm z-50 relative">
        <p className="font-medium mb-1">{label}</p>
        {payload.map((entry: any, index: number) => (
          <div key={index} className="flex items-center space-x-2">
            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
            <span className="text-muted-foreground">{entry.name}:</span>
            <span className="font-medium">{formatNumber(entry.value, formatType)}</span>
          </div>
        ))}
      </div>
    );
  }
  return null;
};
