import React from 'react';
import { AlertCircle } from 'lucide-react';
import { EvidenceArtifact } from '@/lib/types/chat';
import { BarChartWidget } from './BarChartWidget';

export function MapPlaceholderWidget({ artifact, xKey, yKey }: { artifact: EvidenceArtifact, xKey: string, yKey: string }) {
  return (
    <div className="space-y-6">
      <div className="h-[200px] flex flex-col items-center justify-center text-muted-foreground border border-dashed rounded-lg bg-muted/10">
         <AlertCircle className="h-8 w-8 mb-2 opacity-50" />
         <p className="font-medium text-foreground">Map visualization coming soon</p>
         <p className="text-xs mt-1">Geographic data detected. Rendering as horizontal bar chart for now.</p>
      </div>
      
      <div className="mt-4">
        <BarChartWidget artifact={artifact} xKey={xKey} yKey={yKey} isHorizontal={true} />
      </div>
    </div>
  );
}
