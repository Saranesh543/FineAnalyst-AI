import React, { useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Brush } from 'recharts';
import { formatNumber, formatTick, CustomTooltip, ChartDefs, COLORS } from './chart-utils';
import { EvidenceArtifact } from '@/lib/types/chat';

export function LineChartWidget({ artifact, xKey, yKey }: { artifact: EvidenceArtifact, xKey: string, yKey: string }) {
  const [hiddenSeries, setHiddenSeries] = useState<Record<string, boolean>>({});
  
  const toggleSeries = (dataKey: string) => {
    setHiddenSeries(prev => ({ ...prev, [dataKey]: !prev[dataKey] }));
  };

  const format = artifact.metadata?.number_format || 'compact';
  const data = artifact.data;
  const showBrush = data.length > 20;

  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data} margin={{ top: 20, right: 30, left: 10, bottom: 100 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.5} />
        <ChartDefs />
        <XAxis dataKey={xKey} tickFormatter={formatTick} minTickGap={30} angle={-45} textAnchor="end" height={60} stroke="rgba(255,255,255,0.2)" tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 12 }} />
        <YAxis tickFormatter={(val) => formatNumber(val, format)} stroke="rgba(255,255,255,0.2)" tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 12 }} />
        <Tooltip content={<CustomTooltip formatType={format} />} />
        <Legend onClick={(e: any) => toggleSeries(String(e.dataKey))} wrapperStyle={{ paddingTop: '20px', cursor: 'pointer', fontSize: '12px', color: 'rgba(255,255,255,0.7)' }} />
        {!hiddenSeries[yKey] && (
          <Line type="monotone" dataKey={yKey} name={artifact.metadata?.y_label || yKey} stroke={COLORS[0]} strokeWidth={4} activeDot={{ r: 8, fill: COLORS[0], stroke: '#000', strokeWidth: 2 }} filter="url(#cyanGlow)" animationDuration={700} animationEasing="ease-out" />
        )}
        {showBrush && <Brush dataKey={xKey} height={30} stroke="#8884d8" />}
      </LineChart>
    </ResponsiveContainer>
  );
}
