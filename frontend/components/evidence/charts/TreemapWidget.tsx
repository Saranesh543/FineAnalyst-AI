import React from 'react';
import { Treemap, ResponsiveContainer, Tooltip } from 'recharts';
import { CustomTooltip } from './chart-utils';
import { EvidenceArtifact } from '@/lib/types/chat';

export function TreemapWidget({ artifact, xKey, yKey }: { artifact: EvidenceArtifact, xKey: string, yKey: string }) {
  const format = artifact.metadata?.number_format || 'compact';
  const data = artifact.data.map(item => ({
    name: item[xKey],
    size: item[yKey],
    ...item
  }));

  return (
    <ResponsiveContainer width="100%" height={400}>
      <Treemap
        data={data}
        dataKey="size"
        aspectRatio={4 / 3}
        stroke="#fff"
        fill="#2563eb"
      >
        <Tooltip content={<CustomTooltip formatType={format} />} />
      </Treemap>
    </ResponsiveContainer>
  );
}
