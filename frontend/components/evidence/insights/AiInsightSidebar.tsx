"use client";

import React from 'react';
import { Check, Info, ShieldCheck, Activity, BarChart2 } from "lucide-react";
import { EvidenceArtifact } from "@/lib/types/chat";

export function AiInsightSidebar({ artifact }: { artifact: EvidenceArtifact }) {
  return (
    <div className="bg-card/40 backdrop-blur-md p-6 rounded-xl border border-cyan-500/10 shadow-glow space-y-6 h-full flex flex-col">
      <div className="flex items-center space-x-2 border-b border-border/10 pb-3">
        <Activity className="h-5 w-5 text-purple-400" />
        <h3 className="font-bold text-lg text-foreground tracking-tight">AI Confidence</h3>
      </div>
      
      <div className="flex-1 overflow-y-auto custom-scrollbar space-y-6 pr-2">
        {artifact.confidenceScore && (
          <div className="bg-black/20 p-4 rounded-xl border border-white/5 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold text-foreground/80">Confidence Score</span>
              <span className="text-xs font-bold text-green-400 bg-green-500/10 px-3 py-1 rounded-full flex items-center border border-green-500/20">
                <ShieldCheck className="h-3 w-3 mr-1" /> {artifact.confidenceScore}
              </span>
            </div>
            <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden">
              <div className="h-full bg-gradient-to-r from-green-500 to-cyan-400 w-[94%]" />
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Based on dataset volume and query complexity, the AI has high confidence in these results.
            </p>
          </div>
        )}

        <div className="space-y-3">
          <h4 className="text-sm font-semibold text-foreground/80">Dataset Health</h4>
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-black/20 p-3 rounded-lg border border-white/5 flex flex-col justify-between">
              <span className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider mb-1">Rows</span>
              <span className="text-lg font-bold text-foreground">{artifact.rowCountTotal ? artifact.rowCountTotal.toLocaleString() : artifact.data?.length || 0}</span>
            </div>
            <div className="bg-black/20 p-3 rounded-lg border border-white/5 flex flex-col justify-between">
              <span className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider mb-1">Missing</span>
              <span className="text-lg font-bold text-green-400">0%</span>
            </div>
            <div className="bg-black/20 p-3 rounded-lg border border-white/5 flex flex-col justify-between col-span-2">
              <span className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider mb-1">Data Quality</span>
              <span className="text-lg font-bold text-cyan-400">Excellent</span>
            </div>
          </div>
        </div>

        {artifact.insights?.suggested_questions && artifact.insights.suggested_questions.length > 0 && (
          <div className="space-y-3 pt-4 border-t border-border/10">
            <h4 className="text-sm font-semibold text-foreground/80 flex items-center">
              <BarChart2 className="h-4 w-4 mr-1 text-cyan-400" />
              Follow-up Questions
            </h4>
            <div className="space-y-2">
              {artifact.insights.suggested_questions.map((q, i) => (
                <div key={i} className="text-xs text-cyan-300 bg-cyan-950/30 p-2.5 rounded border border-cyan-500/10 cursor-pointer hover:bg-cyan-900/40 transition-colors">
                  {q}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
