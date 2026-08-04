"use client";

import { EvidenceArtifact } from "@/lib/types/chat";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Code2, Database, AlertCircle, Lightbulb, TrendingUp, TrendingDown, ArrowRight } from "lucide-react";
import {
  BarChart, Bar,
  LineChart, Line,
  PieChart, Pie, Cell,
  ScatterChart, Scatter,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';

interface EvidenceArtifactRendererProps {
  evidence: EvidenceArtifact[];
}

const COLORS = ['#2563eb', '#16a34a', '#dc2626', '#eab308', '#9333ea', '#0891b2', '#f97316', '#14b8a6'];

const formatNumber = (value: any, formatType?: string) => {
  if (value === null || value === undefined) return '-';
  const numValue = Number(value);
  if (isNaN(numValue)) return String(value);

  if (formatType === 'currency' || String(value).includes('$')) {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(numValue);
  }
  if (formatType === 'percentage' || String(value).includes('%')) {
    // LLM might return 42.3 for 42.3% or 0.423. Let's assume > 1 means it's already a percentage whole number, else fraction.
    const pctVal = numValue > 1 ? numValue / 100 : numValue;
    return new Intl.NumberFormat('en-US', { style: 'percent', maximumFractionDigits: 1 }).format(pctVal);
  }
  if (formatType === 'compact' || numValue >= 10000) {
    return new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 }).format(numValue);
  }
  if (formatType === 'decimal') {
    return new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(numValue);
  }
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(numValue);
};

const formatTick = (val: any) => {
  if (typeof val === 'string' && val.length > 15) {
    return val.substring(0, 15) + '...';
  }
  return formatNumber(val, 'compact');
};

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-background border rounded-lg shadow-lg p-3 text-sm">
        <p className="font-medium mb-1">{label}</p>
        {payload.map((entry: any, index: number) => (
          <div key={index} className="flex items-center space-x-2">
            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
            <span className="text-muted-foreground">{entry.name}:</span>
            <span className="font-medium">{formatNumber(entry.value)}</span>
          </div>
        ))}
      </div>
    );
  }
  return null;
};

export function EvidenceArtifactRenderer({ evidence }: EvidenceArtifactRendererProps) {
  if (!evidence || evidence.length === 0) return null;

  return (
    <div className="flex flex-col space-y-8 mt-8 border-t pt-8">
      {evidence.map((artifact) => {
        const insights = artifact.insights;
        
        // Auto-detect keys if none provided
        let xKey = artifact.encoding?.x;
        let yKey = artifact.encoding?.y;
        
        if (!xKey || !yKey) {
          if (artifact.data && artifact.data.length > 0) {
            const keys = Object.keys(artifact.data[0]);
            xKey = xKey || keys.find(k => typeof artifact.data[0][k] === 'string') || keys[0];
            yKey = yKey || keys.find(k => typeof artifact.data[0][k] === 'number') || keys[1] || keys[0];
          }
        }

        const renderChart = () => {
          if (!artifact.data || artifact.data.length === 0) {
            return (
              <div className="h-[300px] flex items-center justify-center text-muted-foreground">
                No data available for visualization.
              </div>
            );
          }

          const type = artifact.chartType || 'bar';
          
          if (type === 'kpi') {
             const kpiCard = insights?.kpi_cards?.[0];
             const kpiVal = kpiCard ? kpiCard.value : (artifact.data[0][yKey!] || artifact.data[0][xKey!]);
             const kpiLabel = kpiCard ? kpiCard.label : (yKey || xKey);
             const format = kpiCard ? kpiCard.format : 'compact';
             
             return (
                <div className="flex flex-col items-center justify-center h-[200px] bg-muted/10 rounded-lg border my-4">
                   <span className="text-5xl font-bold text-primary tracking-tight">{formatNumber(kpiVal, format)}</span>
                   <span className="text-muted-foreground mt-3 text-lg font-medium uppercase tracking-wider">{kpiLabel}</span>
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

          if (type === 'data_grid' || type === 'table') {
            const keys = Object.keys(artifact.data[0]);
            return (
              <div className="overflow-x-auto max-h-[400px] overflow-y-auto rounded-md border">
                <table className="w-full text-sm text-left">
                  <thead className="text-xs text-muted-foreground bg-muted/50 uppercase sticky top-0">
                    <tr>
                      {keys.map(k => <th key={k} className="px-4 py-3">{k}</th>)}
                    </tr>
                  </thead>
                  <tbody>
                    {artifact.data.map((row, i) => (
                      <tr key={i} className="border-b last:border-0 hover:bg-muted/20">
                        {keys.map(k => <td key={k} className="px-4 py-3 font-mono text-xs">{String(row[k])}</td>)}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            );
          }

          if (type === 'map') {
             return (
                <div className="h-[300px] flex flex-col items-center justify-center text-muted-foreground border border-dashed rounded-lg bg-muted/10">
                   <AlertCircle className="h-8 w-8 mb-2 opacity-50" />
                   <p>Geographic data detected.</p>
                   <p className="text-xs mt-1">Map component architecture prepared but mapping library not yet integrated.</p>
                </div>
             );
          }
          
          const ChartWrapper = ({ children }: { children: React.ReactNode }) => (
            <ResponsiveContainer width="100%" height={350}>
              {children as any}
            </ResponsiveContainer>
          );

          switch (type) {
            case 'line':
              return (
                <ChartWrapper>
                  <LineChart data={artifact.data} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.5} />
                    <XAxis dataKey={xKey} tickFormatter={formatTick} minTickGap={30} angle={-45} textAnchor="end" height={60} />
                    <YAxis tickFormatter={(val) => formatNumber(val, 'compact')} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend wrapperStyle={{ paddingTop: '20px' }} />
                    <Line type="monotone" dataKey={yKey} name={yKey} stroke="#2563eb" strokeWidth={3} activeDot={{ r: 8 }} />
                  </LineChart>
                </ChartWrapper>
              );
            case 'pie':
              return (
                <ChartWrapper>
                  <PieChart margin={{ top: 20, right: 20, left: 20, bottom: 20 }}>
                    <Tooltip content={<CustomTooltip />} />
                    <Legend wrapperStyle={{ paddingTop: '20px' }} />
                    <Pie
                      data={artifact.data}
                      dataKey={yKey!}
                      nameKey={xKey!}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={120}
                      fill="#8884d8"
                      paddingAngle={2}
                      label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                      labelLine={false}
                    >
                      {artifact.data.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                  </PieChart>
                </ChartWrapper>
              );
            case 'scatter':
              return (
                <ChartWrapper>
                  <ScatterChart margin={{ top: 20, right: 30, bottom: 60, left: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" opacity={0.5} />
                    <XAxis type="number" dataKey={xKey} name={xKey} tickFormatter={(val) => formatNumber(val, 'compact')} />
                    <YAxis type="number" dataKey={yKey} name={yKey} tickFormatter={(val) => formatNumber(val, 'compact')} />
                    <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: '3 3' }} />
                    <Legend wrapperStyle={{ paddingTop: '20px' }} />
                    <Scatter name={artifact.title} data={artifact.data} fill="#2563eb" />
                  </ScatterChart>
                </ChartWrapper>
              );
            case 'bar':
            default:
              return (
                <ChartWrapper>
                  <BarChart data={artifact.data} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.5} />
                    <XAxis dataKey={xKey} tickFormatter={formatTick} minTickGap={30} angle={-45} textAnchor="end" height={60} />
                    <YAxis tickFormatter={(val) => formatNumber(val, 'compact')} />
                    <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(0,0,0,0.05)' }} />
                    <Legend wrapperStyle={{ paddingTop: '20px' }} />
                    <Bar dataKey={yKey} name={yKey} fill="#2563eb" radius={[4, 4, 0, 0]} maxBarSize={60} />
                  </BarChart>
                </ChartWrapper>
              );
          }
        };

        return (
          <div key={artifact.id} className="space-y-6">
            {/* Header & SQL */}
            <Card className="shadow-sm">
              <CardHeader className="bg-muted/20 pb-4 border-b">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div className="flex items-center space-x-2">
                    <Database className="h-5 w-5 text-primary" />
                    <CardTitle className="text-lg">{artifact.title}</CardTitle>
                  </div>
                  <div className="flex items-center space-x-3 text-sm">
                    {artifact.confidenceScore && (
                      <span className={`px-2.5 py-1 rounded-full text-xs font-medium border ${
                        artifact.confidenceScore.toLowerCase() === 'high' ? 'bg-green-100 text-green-700 border-green-200' :
                        artifact.confidenceScore.toLowerCase() === 'medium' ? 'bg-yellow-100 text-yellow-700 border-yellow-200' :
                        'bg-red-100 text-red-700 border-red-200'
                      }`}>
                        {artifact.confidenceScore} Confidence
                      </span>
                    )}
                    <span className="font-mono bg-muted px-2 py-1 rounded border text-muted-foreground">{artifact.rowCountTotal} rows</span>
                  </div>
                </div>
                <CardDescription className="flex items-start mt-3 space-x-2">
                  <Code2 className="h-4 w-4 mt-0.5 text-muted-foreground shrink-0" />
                  <span className="font-mono text-xs break-all text-muted-foreground p-2 bg-muted/30 rounded w-full border">
                    {artifact.sql}
                  </span>
                </CardDescription>
              </CardHeader>

              {/* KPI Cards */}
              {insights?.kpi_cards && insights.kpi_cards.length > 0 && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 border-b bg-muted/5">
                  {insights.kpi_cards.map((kpi, idx) => (
                    <div key={idx} className="bg-background border rounded-lg p-4 shadow-sm flex flex-col justify-center">
                      <span className="text-xs text-muted-foreground uppercase tracking-wider mb-1">{kpi.label}</span>
                      <span className="text-2xl font-bold tracking-tight">{formatNumber(kpi.value, kpi.format)}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Visualization */}
              <CardContent className="p-2 sm:p-6">
                {renderChart()}
              </CardContent>
            </Card>

            {/* AI Insights & Recommendations */}
            {insights && (
              <div className="grid md:grid-cols-2 gap-6">
                <Card className="shadow-sm border-l-4 border-l-primary h-full">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base flex items-center space-x-2">
                      <Lightbulb className="h-4 w-4 text-primary" />
                      <span>Key Findings</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="text-sm space-y-3">
                    <p className="text-muted-foreground">{insights.summary}</p>
                    <ul className="space-y-2">
                      {insights.key_findings?.map((finding, idx) => (
                        <li key={idx} className="flex items-start space-x-2">
                          <span className="text-primary mt-1">•</span>
                          <span>{finding}</span>
                        </li>
                      ))}
                    </ul>
                    {insights.anomalies && insights.anomalies.length > 0 && (
                      <div className="mt-4 pt-4 border-t border-dashed">
                        <span className="text-xs font-semibold uppercase text-amber-600 tracking-wider mb-2 block">Detected Anomalies</span>
                        <ul className="space-y-1">
                          {insights.anomalies.map((anom, idx) => (
                            <li key={idx} className="flex items-start space-x-2 text-amber-700/80">
                              <AlertCircle className="h-3 w-3 mt-0.5" />
                              <span className="text-xs">{anom}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </CardContent>
                </Card>

                <Card className="shadow-sm border-l-4 border-l-green-500 h-full bg-green-50/30">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base flex items-center space-x-2 text-green-700">
                      <TrendingUp className="h-4 w-4" />
                      <span>Business Recommendations</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="text-sm">
                    <ul className="space-y-3">
                      {insights.recommendations?.map((rec, idx) => (
                        <li key={idx} className="flex items-start space-x-2">
                          <ArrowRight className="h-4 w-4 mt-0.5 text-green-600 shrink-0" />
                          <span className="text-muted-foreground leading-relaxed">{rec}</span>
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
