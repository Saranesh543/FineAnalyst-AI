import React from 'react';
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { CustomTooltip, COLORS } from './chart-utils';
import { EvidenceArtifact } from '@/lib/types/chat';

export function PieChartWidget({ artifact, xKey, yKey, isDonut = false }: { artifact: EvidenceArtifact, xKey: string, yKey: string, isDonut?: boolean }) {
  const format = artifact.metadata?.number_format || 'compact';
  const data = artifact.data;

  return (
    <ResponsiveContainer width="100%" height="100%">
      <PieChart margin={{ top: 20, right: 20, left: 20, bottom: 20 }}>
        <Tooltip content={<CustomTooltip formatType={format} />} />
        <Legend wrapperStyle={{ paddingTop: '20px' }} />
        <Pie
          data={data}
          dataKey={yKey}
          nameKey={xKey}
          cx="50%"
          cy="50%"
          innerRadius={isDonut ? 80 : 0}
          outerRadius={120}
          fill="#8884d8"
          paddingAngle={2}
          label={data.length <= 8 ? ({ name, percent }) => `${name} ${((percent || 0) * 100).toFixed(0)}%` : false}
          labelLine={data.length <= 8}
        >
          {data.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
          ))}
        </Pie>
      </PieChart>
    </ResponsiveContainer>
  );
}
