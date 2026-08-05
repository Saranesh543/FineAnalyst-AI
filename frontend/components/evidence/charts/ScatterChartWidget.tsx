import React from 'react';
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { formatNumber, CustomTooltip, ChartDefs, COLORS } from './chart-utils';
import { EvidenceArtifact } from '@/lib/types/chat';

export function ScatterChartWidget({ artifact, xKey, yKey }: { artifact: EvidenceArtifact, xKey: string, yKey: string }) {
  const format = artifact.metadata?.number_format || 'compact';
  const data = artifact.data;

  return (
    <ResponsiveContainer width="100%" height="100%">
      <ScatterChart margin={{ top: 20, right: 30, left: 10, bottom: 40 }}>
        <ChartDefs />
        <CartesianGrid strokeDasharray="3 3" opacity={0.5} />
        <XAxis type="number" dataKey={xKey} name={artifact.metadata?.x_label || xKey} tickFormatter={(val) => formatNumber(val, 'compact')} stroke="rgba(255,255,255,0.2)" tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 12 }} />
        <YAxis type="number" dataKey={yKey} name={artifact.metadata?.y_label || yKey} tickFormatter={(val) => formatNumber(val, format)} stroke="rgba(255,255,255,0.2)" tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 12 }} />
        <Tooltip content={<CustomTooltip formatType={format} />} cursor={{ strokeDasharray: '3 3', stroke: 'rgba(34,211,238,0.2)' }} />
        <Legend wrapperStyle={{ paddingTop: '20px', fontSize: '12px', color: 'rgba(255,255,255,0.7)' }} />
        <Scatter name={artifact.title} data={data} fill={COLORS[0]} filter="url(#cyanGlow)" animationDuration={700} animationEasing="ease-out" />
      </ScatterChart>
    </ResponsiveContainer>
  );
}
