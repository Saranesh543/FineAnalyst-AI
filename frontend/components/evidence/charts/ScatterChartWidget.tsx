import React from 'react';
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { formatNumber, CustomTooltip } from './chart-utils';
import { EvidenceArtifact } from '@/lib/types/chat';

export function ScatterChartWidget({ artifact, xKey, yKey }: { artifact: EvidenceArtifact, xKey: string, yKey: string }) {
  const format = artifact.metadata?.number_format || 'compact';
  const data = artifact.data;

  return (
    <ResponsiveContainer width="100%" height="100%">
      <ScatterChart margin={{ top: 20, right: 30, left: 10, bottom: 40 }}>
        <CartesianGrid strokeDasharray="3 3" opacity={0.5} />
        <XAxis type="number" dataKey={xKey} name={artifact.metadata?.x_label || xKey} tickFormatter={(val) => formatNumber(val, 'compact')} />
        <YAxis type="number" dataKey={yKey} name={artifact.metadata?.y_label || yKey} tickFormatter={(val) => formatNumber(val, format)} />
        <Tooltip content={<CustomTooltip formatType={format} />} cursor={{ strokeDasharray: '3 3' }} />
        <Legend wrapperStyle={{ paddingTop: '20px' }} />
        <Scatter name={artifact.title} data={data} fill="#2563eb" />
      </ScatterChart>
    </ResponsiveContainer>
  );
}
