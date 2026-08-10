"use client";

import React, { useState } from 'react';
import { Check, Copy, ChevronDown, ChevronUp, Terminal } from "lucide-react";
import { Button } from "@/components/ui/button";

export function SqlViewer({ sql }: { sql: string }) {
  const [copied, setCopied] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const copySQL = () => {
    navigator.clipboard.writeText(sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formatSQL = (rawSql: string) => {
    // If it already has multiple lines, assume it's formatted
    if (rawSql.split('\n').length > 2) return rawSql;
    
    return rawSql
      .replace(/\s+(FROM|WHERE|GROUP BY|ORDER BY|LIMIT|HAVING|JOIN|LEFT JOIN|RIGHT JOIN|INNER JOIN)\s+/gi, '\n$1 ')
      .replace(/^(SELECT)\s+/i, '$1\n    ')
      .replace(/,\s*/g, ',\n    ');
  };

  const displaySql = formatSQL(sql.trim());
  const lines = displaySql.split('\n');
  const displayLines = expanded ? lines : lines.slice(0, 15);
  const isTruncated = lines.length > 15;

  // Simple pseudo-syntax highlighting by colorizing keywords
  const highlightLine = (line: string) => {
    const keywords = /\b(SELECT|FROM|WHERE|GROUP BY|ORDER BY|LIMIT|ASC|DESC|JOIN|ON|AND|OR|AS|COUNT|SUM|AVG|MIN|MAX|HAVING|INNER|LEFT|RIGHT|OUTER|WITH)\b/gi;
    const parts = line.split(keywords);
    
    return parts.map((part, i) => {
      if (keywords.test(part)) {
        return <span key={i} className="text-pink-400 font-bold">{part}</span>;
      }
      return <span key={i} className="text-cyan-100">{part}</span>;
    });
  };

  return (
    <div className="bg-card/40 backdrop-blur-md p-6 rounded-xl border border-cyan-500/10 shadow-glow flex flex-col h-full animate-in fade-in duration-500">
      <div className="flex items-center justify-between mb-4 pb-2 border-b border-border/10">
        <h3 className="font-bold text-lg text-foreground flex items-center">
          <Terminal className="h-5 w-5 mr-2 text-cyan-400" />
          Source Query
        </h3>
        <Button variant="ghost" size="sm" className="h-8 text-xs font-semibold text-muted-foreground hover:text-foreground" onClick={copySQL}>
          {copied ? <Check className="h-4 w-4 mr-1 text-green-500" /> : <Copy className="h-4 w-4 mr-1" />}
          {copied ? 'Copied' : 'Copy SQL'}
        </Button>
      </div>
      
      <div className="relative flex-1 overflow-hidden flex flex-col rounded-xl border border-white/5 bg-black/60 shadow-inner">
        <div className="flex-1 overflow-y-auto custom-scrollbar p-4">
          <table className="w-full text-xs sm:text-sm font-mono border-spacing-0">
            <tbody>
              {displayLines.map((line, i) => (
                <tr key={i} className="group hover:bg-white/5 transition-colors">
                  <td className="w-8 pr-4 text-right select-none border-r border-white/10 text-white/30 group-hover:text-white/50 py-0.5">
                    {i + 1}
                  </td>
                  <td className="pl-4 py-0.5 whitespace-pre-wrap break-words">
                    {highlightLine(line)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {isTruncated && !expanded && (
            <div className="absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t from-black/90 to-transparent flex items-end justify-center pb-2 pointer-events-none">
            </div>
          )}
        </div>
        
        {isTruncated && (
          <div className="border-t border-white/10 bg-white/5 flex items-center justify-center p-2 z-10">
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={() => setExpanded(!expanded)}
              className="text-xs h-6 text-cyan-400 hover:text-cyan-300 hover:bg-cyan-950/30"
            >
              {expanded ? (
                <><ChevronUp className="h-3 w-3 mr-1" /> Show Less</>
              ) : (
                <><ChevronDown className="h-3 w-3 mr-1" /> Show Full Query ({lines.length} lines)</>
              )}
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
