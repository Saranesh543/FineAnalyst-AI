"use client";

import { TrendingUp, Users, PieChart, LineChart, DollarSign, Database, FileSpreadsheet, ArrowRight, Loader2 } from "lucide-react";
import { Composer } from "./Composer";
import { useEffect, useState, useMemo } from "react";
import { agentClient, SchemaResponse } from "@/lib/api/agent-client";
import { useAuthStore } from "@/lib/store/auth-store";

interface EmptyStateProps {
  onSelectPrompt: (prompt: string) => void;
  isStreaming: boolean;
}

export function EmptyState({ onSelectPrompt, isStreaming }: EmptyStateProps) {
  const { user } = useAuthStore();
  const [schema, setSchema] = useState<SchemaResponse | null>(null);
  const [loadingSchema, setLoadingSchema] = useState(true);

  const greeting = useMemo(() => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good Morning";
    if (hour < 17) return "Good Afternoon";
    return "Good Evening";
  }, []);

  useEffect(() => {
    agentClient.getSchema()
      .then(res => {
        setSchema(res);
        setLoadingSchema(false);
      })
      .catch(err => {
        console.error("Failed to load schema", err);
        setLoadingSchema(false);
      });
  }, []);

  const suggestions = [
    { title: "Revenue Trends", desc: "Analyze sales over time", icon: TrendingUp, color: "text-blue-400" },
    { title: "Top Customers", desc: "Who are our top customers?", icon: Users, color: "text-green-400" },
    { title: "Product Performance", desc: "Which products are performing best?", icon: PieChart, color: "text-orange-400" },
    { title: "Sales Forecast", desc: "Predict future sales trends", icon: LineChart, color: "text-purple-400" },
    { title: "Profit Analysis", desc: "Analyze profit & margins", icon: DollarSign, color: "text-cyan-400" },
  ];

  const hasTables = schema && schema.tables && schema.tables.length > 0;

  return (
    <div className="flex flex-col items-center justify-center min-h-full py-12 px-4 max-w-[1000px] mx-auto space-y-12 w-full animate-in fade-in slide-in-from-bottom-8 duration-1000">
      {/* Hero Header */}
      <div className="relative text-center space-y-4 w-full">
        <div className="absolute inset-0 bg-cyan-500/5 blur-[80px] -z-10 rounded-[100%]" />
        <h1 className="text-[2.75rem] leading-tight font-semibold tracking-tight text-foreground">
          {greeting},{user?.name ? (
            <> <span className="text-cyan-400 font-bold">{user?.full_name}!</span> 👋</>
          ) : (
            " 👋"
          )}
        </h1>
        <p className="text-muted-foreground text-lg md:text-xl max-w-2xl mx-auto font-light">
          Ask anything about your data, and let AI turn it into insights.
        </p>
      </div>

      {/* Composer Area */}
      <div className="relative w-full">
        <div className="absolute inset-0 bg-cyan-500/5 blur-[60px] -z-10 rounded-[100%]" />
        <Composer onSend={onSelectPrompt} isStreaming={isStreaming} className="w-full" />
      </div>

      {/* Suggestion Cards */}
      <div className="w-full space-y-4">
        <h2 className="text-sm font-semibold text-foreground/80">Try asking about</h2>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {suggestions.map((item, idx) => (
            <button
              key={idx}
              onClick={() => onSelectPrompt(item.desc)}
              className="flex flex-col items-start text-left p-4 rounded-2xl bg-card border border-border/10 shadow-sm hover:-translate-y-1 hover:shadow-[0_0_20px_rgba(34,211,238,0.15)] hover:border-cyan-500/30 transition-all group duration-300"
            >
              <item.icon className={`h-6 w-6 mb-4 ${item.color} group-hover:scale-110 transition-transform duration-300`} />
              <h3 className="font-semibold text-sm mb-1 text-foreground/90">{item.title}</h3>
              <p className="text-xs text-muted-foreground leading-relaxed">{item.desc}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Recent Data Sources */}
      {(loadingSchema || hasTables) && (
        <div className="w-full space-y-4">
          <div className="flex justify-between items-end">
            <h2 className="text-sm font-semibold text-foreground/80">Recent Data Sources</h2>
            <button className="text-xs text-cyan-400 hover:text-cyan-300 font-medium flex items-center gap-1 transition-colors">
              View all <ArrowRight className="h-3 w-3" />
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {loadingSchema ? (
              <div className="flex items-center gap-3 p-3 rounded-2xl bg-card border border-border/10 shadow-sm col-span-1">
                <Loader2 className="h-5 w-5 text-cyan-400 animate-spin" />
                <span className="text-sm text-muted-foreground">Loading database...</span>
              </div>
            ) : hasTables ? (
              <div className="flex items-center gap-3 p-3 rounded-2xl bg-card border border-border/10 shadow-sm col-span-1">
                <div className="h-10 w-10 rounded-xl bg-cyan-500/20 flex items-center justify-center shrink-0">
                  <Database className="h-5 w-5 text-cyan-400" />
                </div>
                <div className="flex flex-col flex-1 overflow-hidden">
                  <span className="font-semibold text-sm truncate text-foreground/90">Primary Database</span>
                  <div className="flex items-center justify-between mt-1">
                    <span className="text-xs text-muted-foreground truncate">{schema.tables.length} tables found</span>
                    <div className="flex items-center justify-center h-4 w-4 rounded-full bg-green-500/20">
                      <div className="h-1.5 w-1.5 rounded-full bg-green-500"></div>
                    </div>
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}
