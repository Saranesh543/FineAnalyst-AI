"use client";

import React, { useRef, useState } from 'react';
import { EvidenceArtifact } from "@/lib/types/chat";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import * as htmlToImage from 'html-to-image';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Loader2, Database, Check, Copy } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

import { KpiCard } from './charts/KpiCard';
import { BarChartWidget } from './charts/BarChartWidget';
import { LineChartWidget } from './charts/LineChartWidget';
import { AreaChartWidget } from './charts/AreaChartWidget';
import { PieChartWidget } from './charts/PieChartWidget';
import { ScatterChartWidget } from './charts/ScatterChartWidget';
import { TreemapWidget } from './charts/TreemapWidget';
import { MapPlaceholderWidget } from './charts/MapPlaceholderWidget';
import { DataGridWidget } from './charts/DataGridWidget';

function EvidenceCard({ artifact }: { artifact: EvidenceArtifact }) {
  const chartRef = useRef<HTMLDivElement>(null);
  const [copiedSQL, setCopiedSQL] = useState(false);
  const [downloadingPNG, setDownloadingPNG] = useState(false);

  let xKey = artifact.metadata?.x_axis || artifact.encoding?.x;
  let yKey = artifact.metadata?.y_axis || artifact.encoding?.y;
  
  if (!xKey || !yKey) {
    if (artifact.data && artifact.data.length > 0) {
      const keys = Object.keys(artifact.data[0]);
      xKey = xKey || keys.find(k => typeof artifact.data[0][k] === 'string') || keys[0];
      yKey = yKey || keys.find(k => typeof artifact.data[0][k] === 'number') || keys[1] || keys[0];
    }
  }

  const chartType = artifact.metadata?.chart_type || artifact.chartType || 'data_grid';
  
  console.error(`[TRACE] EvidenceArtifactRenderer Props: chartType=${chartType}, title=${artifact.title}, data.length=${artifact.data?.length}, xKey=${xKey}, yKey=${yKey}, metadata=${JSON.stringify(artifact.metadata)}`);
  
  // Instrument logging as requested
  if (process.env.NODE_ENV === 'development') {
    console.log("Chart Metadata Debug:", {
      chart_type: chartType,
      title: artifact.metadata?.title,
      subtitle: artifact.metadata?.subtitle,
      x_axis: xKey,
      y_axis: yKey,
      number_format: artifact.metadata?.number_format,
      confidence: artifact.metadata?.confidence || artifact.confidenceScore
    });
  }

  const downloadCSV = () => {
    if (!artifact.data || artifact.data.length === 0) return;
    const headers = Object.keys(artifact.data[0]).join(',');
    const rows = artifact.data.map(row => Object.values(row).map(val => `"${val}"`).join(',')).join('\n');
    const csv = `${headers}\n${rows}`;
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${artifact.metadata?.title || 'export'}.csv`.toLowerCase().replace(/\s+/g, '_');
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const downloadPNG = () => {
    if (chartRef.current) {
      setDownloadingPNG(true);
      htmlToImage.toPng(chartRef.current, { backgroundColor: '#ffffff' })
        .then(function (dataUrl) {
          const a = document.createElement('a');
          a.href = dataUrl;
          a.download = `${artifact.metadata?.title || 'chart'}.png`.toLowerCase().replace(/\s+/g, '_');
          a.click();
        })
        .catch(function (error) {
          console.error('oops, something went wrong!', error);
        })
        .finally(() => setDownloadingPNG(false));
    }
  };

  const copySQL = () => {
    if (artifact.sql) {
      navigator.clipboard.writeText(artifact.sql);
      setCopiedSQL(true);
      setTimeout(() => setCopiedSQL(false), 2000);
    }
  };

  const renderChart = () => {
    if (!artifact.data || artifact.data.length === 0) {
      return (
        <div className="h-[300px] flex items-center justify-center text-muted-foreground bg-muted/10 rounded-lg border">
          No visualization available.
        </div>
      );
    }

    const needsAxes = !['kpi', 'data_grid', 'map'].includes(chartType);
    if (needsAxes && (!xKey || !yKey)) {
      return (
        <div className="h-[300px] flex flex-col items-center justify-center text-muted-foreground bg-muted/10 rounded-lg border">
          <Database className="h-8 w-8 text-muted-foreground/50 mb-2" />
          <p>Visualization unavailable</p>
          <p className="text-xs text-muted-foreground mt-1">Unable to render this visualization due to missing axis data.</p>
        </div>
      );
    }

    switch (chartType) {
      case 'kpi':
        return <KpiCard artifact={artifact} xKey={xKey!} yKey={yKey!} />;
      case 'bar':
        return <BarChartWidget artifact={artifact} xKey={xKey!} yKey={yKey!} />;
      case 'horizontal_bar':
        return <BarChartWidget artifact={artifact} xKey={xKey!} yKey={yKey!} isHorizontal={true} />;
      case 'line':
        return <LineChartWidget artifact={artifact} xKey={xKey!} yKey={yKey!} />;
      case 'area':
        return <AreaChartWidget artifact={artifact} xKey={xKey!} yKey={yKey!} />;
      case 'pie':
        return <PieChartWidget artifact={artifact} xKey={xKey!} yKey={yKey!} />;
      case 'donut':
        return <PieChartWidget artifact={artifact} xKey={xKey!} yKey={yKey!} isDonut={true} />;
      case 'scatter':
        return <ScatterChartWidget artifact={artifact} xKey={xKey!} yKey={yKey!} />;
      case 'treemap':
        return <TreemapWidget artifact={artifact} xKey={xKey!} yKey={yKey!} />;
      case 'map':
        return <MapPlaceholderWidget artifact={artifact} xKey={xKey!} yKey={yKey!} />;
      case 'data_grid':
        return <DataGridWidget artifact={artifact} />;
      default:
        return <DataGridWidget artifact={artifact} />;
    }
  };

  return (
    <Card className="shadow-sm">
      <CardHeader className="bg-muted/20 pb-4 border-b">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex flex-col">
            <div className="flex items-center space-x-2">
              <Database className="h-5 w-5 text-primary" />
              <CardTitle className="text-lg">{artifact.metadata?.title || artifact.title}</CardTitle>
            </div>
            {artifact.metadata?.subtitle && (
              <p className="text-sm text-muted-foreground mt-1 ml-7">{artifact.metadata.subtitle}</p>
            )}
          </div>
          <div className="flex items-center space-x-2">
            <TooltipProvider>
              
              {/* SQL Dialog */}
              <Dialog>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <DialogTrigger asChild>
                      <Button variant="outline" size="sm" className="h-8 text-xs font-semibold">
                        <span className="mr-1">📋</span> SQL
                      </Button>
                    </DialogTrigger>
                  </TooltipTrigger>
                  <TooltipContent>View source query</TooltipContent>
                </Tooltip>
                <DialogContent className="max-w-2xl">
                  <DialogHeader>
                    <DialogTitle>Generated SQL</DialogTitle>
                  </DialogHeader>
                  <div className="relative">
                    <pre className="p-4 bg-muted rounded-md overflow-x-auto text-sm text-foreground">
                      <code>{artifact.sql}</code>
                    </pre>
                    <Button variant="secondary" size="sm" className="absolute top-2 right-2" onClick={copySQL}>
                      {copiedSQL ? <Check className="h-4 w-4 mr-1 text-green-600" /> : <Copy className="h-4 w-4 mr-1" />}
                      {copiedSQL ? 'Copied' : 'Copy'}
                    </Button>
                  </div>
                </DialogContent>
              </Dialog>

              {/* CSV Download */}
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="outline" size="sm" className="h-8 text-xs font-semibold" onClick={downloadCSV} disabled={!artifact.data?.length}>
                    <span className="mr-1">⬇</span> CSV
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Download raw data</TooltipContent>
              </Tooltip>
              
              {/* PNG Download */}
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="outline" size="sm" className="h-8 text-xs font-semibold" onClick={downloadPNG} disabled={downloadingPNG || !artifact.data?.length}>
                    {downloadingPNG ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <span className="mr-1">🖼</span>} PNG
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Download chart image</TooltipContent>
              </Tooltip>
              
              {/* Expand Dialog */}
              <Dialog>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <DialogTrigger asChild>
                      <Button variant="outline" size="sm" className="h-8 text-xs font-semibold">
                        <span className="mr-1">⛶</span> Expand
                      </Button>
                    </DialogTrigger>
                  </TooltipTrigger>
                  <TooltipContent>Open fullscreen report</TooltipContent>
                </Tooltip>
                <DialogContent className="sm:max-w-[95vw] lg:max-w-[1400px] w-full max-h-[90vh] flex flex-col p-0 overflow-hidden bg-background border-border/20 shadow-2xl">
                <DialogHeader className="sticky top-0 z-10 shrink-0 bg-card/80 backdrop-blur-xl p-6 border-b border-border/10 shadow-sm">
                  <div className="flex items-center space-x-2">
                    <Database className="h-6 w-6 text-cyan-400" />
                    <DialogTitle className="text-2xl font-bold text-foreground tracking-tight">{artifact.metadata?.title || artifact.title}</DialogTitle>
                  </div>
                </DialogHeader>
                
                <div className="p-6 space-y-6 flex-1 overflow-y-auto custom-scrollbar bg-background/50">
                  {/* KPIs */}
                  {artifact.insights?.kpi_cards?.length ? (
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                      {artifact.insights.kpi_cards.map((kpi, idx) => (
                        <div key={idx} className="bg-card/40 backdrop-blur-md p-4 rounded-xl border border-cyan-500/10 shadow-glow transition-all hover:-translate-y-1 hover:shadow-[0_0_20px_rgba(34,211,238,0.1)]">
                          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">{kpi.label}</p>
                          <p className="text-3xl font-bold text-cyan-400 mt-2">{kpi.value}</p>
                        </div>
                      ))}
                    </div>
                  ) : null}

                  {/* Chart (70%) and Insights (30%) */}
                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    <div className="lg:col-span-2 bg-card/40 backdrop-blur-md p-6 rounded-xl border border-cyan-500/10 shadow-glow h-[500px]">
                      {renderChart()}
                    </div>
                    
                    <div className="lg:col-span-1 bg-card/40 backdrop-blur-md p-6 rounded-xl border border-cyan-500/10 shadow-glow space-y-6 overflow-y-auto h-[500px] custom-scrollbar">
                      {artifact.confidenceScore && (
                        <div>
                          <div className="flex items-center space-x-2">
                            <span className="text-sm font-semibold text-foreground">AI Confidence:</span>
                            <span className="text-xs font-bold text-green-400 bg-green-500/20 px-3 py-1 rounded-full flex items-center">
                              <Check className="h-3 w-3 mr-1" /> {artifact.confidenceScore}
                            </span>
                          </div>
                        </div>
                      )}

                      {artifact.insights?.key_findings?.length ? (
                        <div className="space-y-3">
                          <h3 className="font-bold text-lg border-b border-border/10 pb-2 text-foreground">Key Insights</h3>
                          <ul className="space-y-3 text-sm">
                            {artifact.insights.key_findings.map((f, i) => (
                              <li key={i} className="flex items-start text-muted-foreground">
                                <span className="mr-2 text-cyan-400 font-bold">•</span> {f}
                              </li>
                            ))}
                          </ul>
                        </div>
                      ) : null}
                    </div>
                  </div>

                  {/* Recommendations */}
                  {artifact.insights?.recommendations?.length ? (
                    <div className="bg-card/40 backdrop-blur-md p-6 rounded-xl border border-cyan-500/10 shadow-glow space-y-3">
                      <h3 className="font-bold text-lg border-b border-border/10 pb-2 text-foreground">Business Recommendations</h3>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-2">
                        {artifact.insights.recommendations.map((r, i) => (
                          <div key={i} className="flex items-start bg-accent/10 p-4 rounded-xl border border-cyan-500/10 transition-all hover:bg-accent/20">
                            <span className="mr-2 text-cyan-400 font-bold">•</span> 
                            <span className="text-sm text-muted-foreground">{r}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : null}

                  {/* SQL */}
                  <div className="bg-card/40 backdrop-blur-md p-6 rounded-xl border border-cyan-500/10 shadow-glow space-y-3">
                     <h3 className="font-bold text-lg border-b border-border/10 pb-2 text-foreground">Source Query</h3>
                     <pre className="p-4 bg-black/40 rounded-xl overflow-x-auto overflow-y-auto max-h-[300px] whitespace-pre-wrap break-words text-sm text-cyan-300 font-mono custom-scrollbar">
                       <code>{artifact.sql}</code>
                     </pre>
                  </div>

                  {/* Raw Data */}
                  {chartType !== 'data_grid' && (
                    <div className="bg-card/40 backdrop-blur-md p-6 rounded-xl border border-cyan-500/10 shadow-glow space-y-3">
                      <h3 className="font-bold text-lg border-b border-border/10 pb-2 text-foreground">Raw Data</h3>
                      <div className="h-[400px]">
                        <DataGridWidget artifact={artifact} />
                      </div>
                    </div>
                  )}
                </div>
              </DialogContent>
              </Dialog>
            </TooltipProvider>
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-6 p-0" ref={chartRef}>
        <div className="bg-white p-6 rounded-b-xl h-[400px]">
          <div className="mb-4 hidden export-only">
             <h2 className="text-xl font-bold">{artifact.metadata?.title || artifact.title}</h2>
             {artifact.metadata?.subtitle && <p className="text-sm text-gray-500">{artifact.metadata.subtitle}</p>}
          </div>
          {renderChart()}
        </div>
      </CardContent>
    </Card>
  );
}

export function EvidenceArtifactRenderer({ evidence }: { evidence: EvidenceArtifact[] }) {
  if (!evidence || evidence.length === 0) return null;

  return (
    <div className="flex flex-col space-y-8 mt-8 border-t pt-8">
      {evidence.map((artifact) => (
        <div key={artifact.id}>
          <EvidenceCard artifact={artifact} />
        </div>
      ))}
    </div>
  );
}
