import React from 'react';
import { CheckCircle2 } from 'lucide-react';
import { formatNumber } from './chart-utils';
import { EvidenceArtifact } from '@/lib/types/chat';

export function KpiCard({ artifact, xKey, yKey }: { artifact: EvidenceArtifact, xKey?: string, yKey?: string }) {
  const kpiCard = artifact.insights?.kpi_cards?.[0];
  const kpiVal = kpiCard ? kpiCard.value : (artifact.data?.[0]?.[yKey!] || artifact.data?.[0]?.[xKey!]);
  const kpiLabel = kpiCard ? kpiCard.label : (yKey || xKey);
  const format = artifact.metadata?.number_format || (kpiCard ? kpiCard.format : 'compact');
  
  return (
    <div className="flex flex-col items-center justify-center h-[200px] bg-card/40 backdrop-blur-md rounded-xl border border-cyan-500/20 shadow-glow my-4 transition-all hover:-translate-y-1 hover:shadow-[0_0_20px_rgba(34,211,238,0.15)] group">
      <span className="text-5xl font-bold text-cyan-400 tracking-tight group-hover:scale-105 transition-transform">{formatNumber(kpiVal, format)}</span>
      <span className="text-muted-foreground mt-3 text-sm font-medium uppercase tracking-wider">{kpiLabel}</span>
      {artifact.confidenceScore && (
        <div className="mt-4 flex items-center space-x-1">
          <CheckCircle2 className="h-4 w-4 text-green-600" />
          <span className="text-xs font-semibold text-green-700 bg-green-100 px-2 py-0.5 rounded-full">
            {artifact.confidenceScore} Confidence
          </span>
        </div>
      )}
    </div>
  );
}
