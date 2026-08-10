import React, { useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Brush } from 'recharts';
import { formatNumber, formatTick, CustomTooltip, ChartDefs, COLORS } from './chart-utils';
import { EvidenceArtifact } from '@/lib/types/chat';

export function BarChartWidget({ artifact, xKey, yKeys, isHorizontal = false }: { artifact: EvidenceArtifact, xKey: string, yKeys: string[], isHorizontal?: boolean }) {
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
      <BarChart data={data} layout="vertical" margin={{ top: 20, right: 30, left: 100, bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} opacity={0.5} />
          <ChartDefs />
          <XAxis type="number" tickFormatter={(val) => formatNumber(val, format)} stroke="rgba(255,255,255,0.2)" tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 12 }} />
          <YAxis type="category" dataKey={xKey} tickFormatter={formatTick} width={90} stroke="rgba(255,255,255,0.2)" tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 12 }} />
          <Tooltip content={<CustomTooltip formatType={format} />} cursor={{ fill: 'rgba(34,211,238,0.05)' }} />
          <Legend onClick={(e: any) => toggleSeries(String(e.dataKey))} wrapperStyle={{ paddingTop: '20px', cursor: 'pointer', fontSize: '12px', color: 'rgba(255,255,255,0.7)' }} />
          {yKeys.map((key, idx) => (
            !hiddenSeries[key] && (
              <Bar key={key} dataKey={key} name={yKeys.length === 1 && artifact.metadata?.y_label ? artifact.metadata.y_label : key} fill={COLORS[idx % COLORS.length]} radius={[0, 4, 4, 0]} maxBarSize={40} filter="url(#cyanGlow)" animationDuration={700} animationEasing="ease-out" />
            )
          ))}
        </BarChart>
      </ResponsiveContainer>
    );
  }

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} margin={{ top: 20, right: 30, left: 10, bottom: 100 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.5} />
        <ChartDefs />
        <XAxis dataKey={xKey} tickFormatter={formatTick} minTickGap={30} angle={-45} textAnchor="end" height={60} stroke="rgba(255,255,255,0.2)" tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 12 }} />
        <YAxis tickFormatter={(val) => formatNumber(val, format)} stroke="rgba(255,255,255,0.2)" tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 12 }} />
        <Tooltip content={<CustomTooltip formatType={format} />} cursor={{ fill: 'rgba(34,211,238,0.05)' }} />
        <Legend onClick={(e: any) => toggleSeries(String(e.dataKey))} wrapperStyle={{ paddingTop: '20px', cursor: 'pointer', fontSize: '12px', color: 'rgba(255,255,255,0.7)' }} />
        {yKeys.map((key, idx) => (
          !hiddenSeries[key] && (
            <Bar key={key} dataKey={key} name={yKeys.length === 1 && artifact.metadata?.y_label ? artifact.metadata.y_label : key} fill={COLORS[idx % COLORS.length]} radius={[4, 4, 0, 0]} maxBarSize={60} filter="url(#cyanGlow)" animationDuration={700} animationEasing="ease-out" />
          )
        ))}
        {showBrush && <Brush dataKey={xKey} height={30} stroke="#8884d8" />}
      </BarChart>
    </ResponsiveContainer>
  );
}
