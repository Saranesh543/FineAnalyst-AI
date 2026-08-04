import React, { useState } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Brush } from 'recharts';
import { formatNumber, formatTick, CustomTooltip } from './chart-utils';
import { EvidenceArtifact } from '@/lib/types/chat';

export function AreaChartWidget({ artifact, xKey, yKey }: { artifact: EvidenceArtifact, xKey: string, yKey: string }) {
  const [hiddenSeries, setHiddenSeries] = useState<Record<string, boolean>>({});
  
  const toggleSeries = (dataKey: string) => {
    setHiddenSeries(prev => ({ ...prev, [dataKey]: !prev[dataKey] }));
  };

  const format = artifact.metadata?.number_format || 'compact';
  const data = artifact.data;
  const showBrush = data.length > 20;

  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={data} margin={{ top: 20, right: 30, left: 10, bottom: 40 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.5} />
        <XAxis dataKey={xKey} tickFormatter={formatTick} minTickGap={30} angle={-45} textAnchor="end" height={60} />
        <YAxis tickFormatter={(val) => formatNumber(val, format)} />
        <Tooltip content={<CustomTooltip formatType={format} />} />
        <Legend onClick={(e: any) => toggleSeries(String(e.dataKey))} wrapperStyle={{ paddingTop: '20px', cursor: 'pointer' }} />
        {!hiddenSeries[yKey] && (
          <Area type="monotone" dataKey={yKey} name={artifact.metadata?.y_label || yKey} stroke="#2563eb" fill="#3b82f6" fillOpacity={0.3} />
        )}
        {showBrush && <Brush dataKey={xKey} height={30} stroke="#8884d8" />}
      </AreaChart>
    </ResponsiveContainer>
  );
}
