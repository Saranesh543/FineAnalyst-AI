import React from 'react';
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { CustomTooltip, COLORS } from './chart-utils';
import { EvidenceArtifact } from '@/lib/types/chat';

export function PieChartWidget({ artifact, xKey, yKey }: { artifact: EvidenceArtifact, xKey: string, yKey: string }) {
  const format = artifact.metadata?.number_format || 'compact';
  const data = artifact.data;

  return (
    <ResponsiveContainer width="100%" height={400}>
      <PieChart margin={{ top: 20, right: 20, left: 20, bottom: 20 }}>
        <Tooltip content={<CustomTooltip formatType={format} />} />
        <Legend wrapperStyle={{ paddingTop: '20px' }} />
        <Pie
          data={data}
          dataKey={yKey}
          nameKey={xKey}
          cx="50%"
          cy="50%"
          innerRadius={60}
          outerRadius={120}
          fill="#8884d8"
          paddingAngle={2}
          label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
          labelLine={false}
        >
          {data.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
          ))}
        </Pie>
      </PieChart>
    </ResponsiveContainer>
  );
}
