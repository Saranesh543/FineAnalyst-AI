"use client";

import React from 'react';
import { Target, ArrowRight, Zap } from "lucide-react";
import { Streamdown } from "streamdown";

interface BusinessRecommendationsProps {
  recommendations: string[];
}

export function BusinessRecommendations({ recommendations }: BusinessRecommendationsProps) {
  if (!recommendations || recommendations.length === 0) return null;

  return (
    <div className="bg-card/40 backdrop-blur-md p-6 rounded-xl border border-cyan-500/10 shadow-glow space-y-6">
      <div className="flex items-center space-x-2 border-b border-border/10 pb-3">
        <Target className="h-5 w-5 text-indigo-400" />
        <h3 className="font-bold text-lg text-foreground tracking-tight">Business Recommendations</h3>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {recommendations.map((rec, i) => {
          // A simple heuristic to assign a priority color based on index
          const isHighPriority = i === 0;
          
          return (
            <div key={i} className="flex flex-col bg-black/20 p-5 rounded-xl border border-white/5 transition-all hover:bg-white/5 hover:border-indigo-500/30 group">
              <div className="flex items-center justify-between mb-3">
                <span className={`text-[10px] font-bold px-2 py-1 rounded-sm uppercase tracking-wider ${isHighPriority ? 'bg-indigo-500/20 text-indigo-300' : 'bg-cyan-500/20 text-cyan-300'}`}>
                  {isHighPriority ? 'High Priority' : 'Opportunity'}
                </span>
                <Zap className={`h-4 w-4 ${isHighPriority ? 'text-indigo-400' : 'text-cyan-400'} opacity-50 group-hover:opacity-100 transition-opacity`} />
              </div>
              <div className="text-sm text-foreground/80 leading-relaxed flex-1 prose prose-sm dark:prose-invert max-w-none prose-p:my-0">
                <Streamdown mode="static">{rec}</Streamdown>
              </div>
              <div className="mt-4 flex items-center text-xs text-muted-foreground font-semibold cursor-pointer group-hover:text-indigo-300 transition-colors">
                Take Action <ArrowRight className="h-3 w-3 ml-1 transform group-hover:translate-x-1 transition-transform" />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
