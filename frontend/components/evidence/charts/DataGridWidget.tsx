"use client";

import React, { useMemo, useState } from 'react';
import DataGrid from 'react-data-grid';
import 'react-data-grid/lib/styles.css';
import { EvidenceArtifact } from '@/lib/types/chat';

export function DataGridWidget({ artifact }: { artifact: EvidenceArtifact }) {
  const data = artifact.data;
  const [sortColumns, setSortColumns] = useState<any[]>([]);

  const columns = useMemo(() => {
    if (!data || data.length === 0) return [];
    return Object.keys(data[0]).map(key => ({
      key,
      name: key.toUpperCase(),
      sortable: true,
      resizable: true,
      minWidth: 120,
    }));
  }, [data]);

  const sortedRows = useMemo(() => {
    if (sortColumns.length === 0) return data || [];
    
    return [...(data || [])].sort((a, b) => {
      for (const sort of sortColumns) {
        const valA = a[sort.columnKey];
        const valB = b[sort.columnKey];
        const compResult = valA === valB ? 0 : (valA > valB ? 1 : -1);
        if (compResult !== 0) {
          return sort.direction === 'ASC' ? compResult : -compResult;
        }
      }
      return 0;
    });
  }, [data, sortColumns]);

  if (!data || data.length === 0) return null;

  return (
    <div className="h-full w-full rdg-dark rounded-xl border border-cyan-500/20 overflow-hidden shadow-glow">
      <style dangerouslySetInnerHTML={{ __html: `
        .rdg-custom-theme {
          --rdg-color: hsl(var(--foreground));
          --rdg-border-color: rgba(34, 211, 238, 0.1);
          --rdg-summary-border-color: rgba(34, 211, 238, 0.1);
          --rdg-background-color: transparent;
          --rdg-header-background-color: rgba(34, 211, 238, 0.05);
          --rdg-row-hover-background-color: rgba(34, 211, 238, 0.1);
          --rdg-row-selected-background-color: rgba(34, 211, 238, 0.15);
          --rdg-row-selected-hover-background-color: rgba(34, 211, 238, 0.2);
          --rdg-selection-color: #22d3ee;
          background: transparent;
          border: none;
        }
        .rdg-custom-theme .rdg-cell {
          border-right: 1px solid rgba(34, 211, 238, 0.05);
          border-bottom: 1px solid rgba(34, 211, 238, 0.05);
        }
        .rdg-custom-theme .rdg-header-row .rdg-cell {
          font-weight: 600;
          color: #22d3ee;
          text-transform: uppercase;
          font-size: 0.75rem;
          letter-spacing: 0.05em;
        }
      `}} />
      <DataGrid
        columns={columns}
        rows={sortedRows}
        className="h-full text-xs font-mono rdg-custom-theme"
        onSortColumnsChange={setSortColumns}
        sortColumns={sortColumns}
      />
    </div>
  );
}
