"use client";

import React from 'react';
import { Sparkles, TrendingUp, AlertTriangle, Lightbulb } from "lucide-react";

interface AiExecutiveSummaryProps {
  insights: {
    summary?: string;
    key_findings?: string[];
    anomalies?: string[];
  };
}

export function AiExecutiveSummary({ insights }: AiExecutiveSummaryProps) {
  if (!insights) return null;

  return (
    <div className="bg-card/40 backdrop-blur-md p-6 rounded-xl border border-cyan-500/10 shadow-glow space-y-6">
      <div className="flex items-center space-x-2 border-b border-border/10 pb-3">
        <Sparkles className="h-5 w-5 text-cyan-400" />
        <h3 className="font-bold text-lg text-foreground tracking-tight">AI Executive Summary</h3>
      </div>
      
      {insights.summary && (
        <div className="text-sm text-foreground/90 leading-relaxed font-medium">
          {insights.summary}
        </div>
      )}

      {insights.key_findings && insights.key_findings.length > 0 && (
        <div className="space-y-3">
          <h4 className="flex items-center text-sm font-semibold text-cyan-400">
            <TrendingUp className="h-4 w-4 mr-2" /> Business Trends
          </h4>
          <ul className="space-y-2">
            {insights.key_findings.map((f, i) => (
              <li key={i} className="flex items-start text-sm text-muted-foreground bg-black/20 p-3 rounded-lg border border-white/5">
                <span className="mr-3 text-cyan-500 font-bold">•</span> 
                <span className="leading-snug">{f}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {insights.anomalies && insights.anomalies.length > 0 && (
        <div className="space-y-3 mt-4">
          <h4 className="flex items-center text-sm font-semibold text-amber-400">
            <AlertTriangle className="h-4 w-4 mr-2" /> Detected Outliers & Risks
          </h4>
          <ul className="space-y-2">
            {insights.anomalies.map((a, i) => (
              <li key={i} className="flex items-start text-sm text-muted-foreground bg-amber-500/10 p-3 rounded-lg border border-amber-500/20">
                <span className="mr-3 text-amber-500 font-bold">•</span> 
                <span className="leading-snug">{a}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
