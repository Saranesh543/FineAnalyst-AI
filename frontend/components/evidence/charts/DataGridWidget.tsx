import React from 'react';
import { EvidenceArtifact } from '@/lib/types/chat';

export function DataGridWidget({ artifact }: { artifact: EvidenceArtifact }) {
  const data = artifact.data;
  if (!data || data.length === 0) return null;
  const keys = Object.keys(data[0]);
  
  return (
    <div className="overflow-x-auto max-h-[400px] overflow-y-auto rounded-md border">
      <table className="w-full text-sm text-left">
        <thead className="text-xs text-muted-foreground bg-muted/50 uppercase sticky top-0 shadow-sm z-10">
          <tr>
            {keys.map(k => <th key={k} className="px-4 py-3 font-semibold">{k}</th>)}
          </tr>
        </thead>
        <tbody className="divide-y">
          {data.map((row, i) => (
            <tr key={i} className="hover:bg-muted/30 transition-colors">
              {keys.map(k => (
                <td key={k} className="px-4 py-3 font-mono text-xs text-muted-foreground whitespace-nowrap">
                  {String(row[k])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
