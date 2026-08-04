import React, { useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Brush } from 'recharts';
import { formatNumber, formatTick, CustomTooltip } from './chart-utils';
import { EvidenceArtifact } from '@/lib/types/chat';

export function BarChartWidget({ artifact, xKey, yKey, isHorizontal = false }: { artifact: EvidenceArtifact, xKey: string, yKey: string, isHorizontal?: boolean }) {
  const [hiddenSeries, setHiddenSeries] = useState<Record<string, boolean>>({});
  
  const toggleSeries = (dataKey: string) => {
    setHiddenSeries(prev => ({ ...prev, [dataKey]: !prev[dataKey] }));
  };

  const format = artifact.metadata?.number_format || 'compact';
  const data = artifact.data;
  const showBrush = data.length > 20;

  if (isHorizontal) {
    return (
      <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} layout="vertical" margin={{ top: 20, right: 30, left: 80, bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} opacity={0.5} />
          <XAxis type="number" tickFormatter={(val) => formatNumber(val, format)} />
          <YAxis type="category" dataKey={xKey} tickFormatter={formatTick} width={90} />
          <Tooltip content={<CustomTooltip formatType={format} />} cursor={{ fill: 'rgba(0,0,0,0.05)' }} />
          <Legend onClick={(e: any) => toggleSeries(String(e.dataKey))} wrapperStyle={{ paddingTop: '20px', cursor: 'pointer' }} />
          {!hiddenSeries[yKey] && (
            <Bar dataKey={yKey} name={artifact.metadata?.y_label || yKey} fill="#2563eb" radius={[0, 4, 4, 0]} maxBarSize={40} />
          )}
        </BarChart>
      </ResponsiveContainer>
    );
  }

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} margin={{ top: 20, right: 30, left: 10, bottom: 40 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.5} />
        <XAxis dataKey={xKey} tickFormatter={formatTick} minTickGap={30} angle={-45} textAnchor="end" height={60} />
        <YAxis tickFormatter={(val) => formatNumber(val, format)} />
        <Tooltip content={<CustomTooltip formatType={format} />} cursor={{ fill: 'rgba(0,0,0,0.05)' }} />
        <Legend onClick={(e: any) => toggleSeries(String(e.dataKey))} wrapperStyle={{ paddingTop: '20px', cursor: 'pointer' }} />
        {!hiddenSeries[yKey] && (
          <Bar dataKey={yKey} name={artifact.metadata?.y_label || yKey} fill="#2563eb" radius={[4, 4, 0, 0]} maxBarSize={60} />
        )}
        {showBrush && <Brush dataKey={xKey} height={30} stroke="#8884d8" />}
      </BarChart>
    </ResponsiveContainer>
  );
}
