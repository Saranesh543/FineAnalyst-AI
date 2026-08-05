"use client";

import React, { useRef, useState } from 'react';
import { EvidenceArtifact } from "@/lib/types/chat";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import * as htmlToImage from 'html-to-image';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Loader2, Database, Check, Copy, Sparkles } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { motion } from "framer-motion";

import { KpiCard } from './charts/KpiCard';
import { BarChartWidget } from './charts/BarChartWidget';
import { LineChartWidget } from './charts/LineChartWidget';
import { AreaChartWidget } from './charts/AreaChartWidget';
import { PieChartWidget } from './charts/PieChartWidget';
import { ScatterChartWidget } from './charts/ScatterChartWidget';
import { TreemapWidget } from './charts/TreemapWidget';
import { MapPlaceholderWidget } from './charts/MapPlaceholderWidget';
import { DataGridWidget } from './charts/DataGridWidget';
import { SqlViewer } from './SqlViewer';
import { AiExecutiveSummary } from './insights/AiExecutiveSummary';
import { BusinessRecommendations } from './insights/BusinessRecommendations';
import { AiInsightSidebar } from './insights/AiInsightSidebar';

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
                <DialogContent className="sm:max-w-[95vw] lg:max-w-[95vw] xl:max-w-[1600px] w-full max-h-[95vh] h-[95vh] flex flex-col p-0 overflow-hidden bg-background/95 backdrop-blur-3xl border-cyan-500/30 shadow-[0_0_50px_rgba(34,211,238,0.15)] rounded-2xl">
                
                {/* Header */}
                <DialogHeader className="sticky top-0 z-20 shrink-0 bg-background/80 backdrop-blur-xl px-6 py-4 border-b border-white/5 shadow-sm flex flex-row items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <div className="h-12 w-12 rounded-xl bg-cyan-500/10 flex items-center justify-center border border-cyan-500/20 shadow-[0_0_15px_rgba(34,211,238,0.2)]">
                      <Database className="h-6 w-6 text-cyan-400" />
                    </div>
                    <div>
                      <DialogTitle className="text-2xl font-bold text-foreground tracking-tight flex items-center">
                        {artifact.metadata?.title || artifact.title}
                        <span className="ml-3 text-[10px] uppercase tracking-wider font-bold bg-cyan-500/10 text-cyan-400 px-2 py-0.5 rounded border border-cyan-500/20">
                          {chartType.replace('_', ' ')}
                        </span>
                      </DialogTitle>
                      <p className="text-sm text-muted-foreground mt-0.5 flex items-center space-x-2">
                        <span>Database: <span className="text-foreground/80 font-medium">FineAnalyst Demo</span></span>
                        <span>•</span>
                        <span>Generated: {new Date().toLocaleDateString()} {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Button variant="outline" size="sm" className="h-9 bg-black/20 border-white/10 hover:bg-white/10" onClick={downloadCSV} disabled={!artifact.data?.length}>
                      <span className="mr-2">⬇</span> Export CSV
                    </Button>
                    <Button variant="outline" size="sm" className="h-9 bg-black/20 border-white/10 hover:bg-white/10" onClick={downloadPNG} disabled={downloadingPNG || !artifact.data?.length}>
                      {downloadingPNG ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <span className="mr-2">🖼</span>} Export Image
                    </Button>
                  </div>
                </DialogHeader>
                
                {/* Body */}
                <div className="flex-1 overflow-y-auto custom-scrollbar bg-background/40 relative">
                  <div className="p-6 md:p-8 space-y-8 max-w-[1600px] mx-auto">
                    
                    {/* KPIs */}
                    {artifact.insights?.kpi_cards?.length ? (
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 animate-in slide-in-from-bottom-4 duration-500">
                        {artifact.insights.kpi_cards.map((kpi, idx) => (
                          <div key={idx} className="bg-card/40 backdrop-blur-md p-5 rounded-2xl border border-cyan-500/10 shadow-glow transition-all hover:-translate-y-1 hover:border-cyan-500/30 hover:shadow-[0_0_30px_rgba(34,211,238,0.15)] group flex flex-col justify-between h-32">
                            <div className="flex justify-between items-start">
                              <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider group-hover:text-cyan-400/80 transition-colors">{kpi.label}</p>
                            </div>
                            <p className="text-4xl font-bold text-cyan-400 tracking-tight">{kpi.value}</p>
                          </div>
                        ))}
                      </div>
                    ) : null}

                    {/* Main Workspace: Chart + Insights */}
                    <div className="grid grid-cols-1 xl:grid-cols-4 gap-8">
                      <div className="xl:col-span-3 space-y-8">
                        {/* Primary Visualization */}
                        <div className="bg-card/40 backdrop-blur-md p-6 rounded-2xl border border-cyan-500/10 shadow-glow h-[500px] flex flex-col animate-in slide-in-from-bottom-6 duration-700">
                           <h3 className="font-bold text-lg border-b border-border/5 pb-3 mb-4 text-foreground flex items-center">
                             Visualization
                           </h3>
                           <div className="flex-1 min-h-0 relative">
                             {renderChart()}
                           </div>
                        </div>

                        {/* Raw Data & SQL */}
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 animate-in slide-in-from-bottom-8 duration-700">
                          {chartType !== 'data_grid' && (
                            <div className="h-[400px]">
                              <DataGridWidget artifact={artifact} />
                            </div>
                          )}
                          <div className="h-[400px]">
                            <SqlViewer sql={artifact.sql} />
                          </div>
                        </div>
                      </div>
                      
                      {/* Right Sidebar (AI Insights & Recommendations) */}
                      <div className="xl:col-span-1 space-y-6 flex flex-col h-full animate-in slide-in-from-right-8 duration-700">
                        <AiInsightSidebar artifact={artifact} />
                        <AiExecutiveSummary insights={artifact.insights || {}} />
                        <BusinessRecommendations recommendations={artifact.insights?.recommendations || []} />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Footer */}
                <div className="sticky bottom-0 z-20 shrink-0 bg-background/95 backdrop-blur-xl px-6 py-3 border-t border-white/5 flex items-center justify-between text-xs text-muted-foreground">
                  <div className="flex items-center space-x-4">
                    <span>Rows Returned: <strong className="text-foreground">{artifact.rowCountTotal || artifact.data?.length || 0}</strong></span>
                    <span>•</span>
                    <span>Execution Time: <strong className="text-foreground">312ms</strong></span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Sparkles className="h-3 w-3 text-cyan-500" />
                    <span>Generated by FineAnalyst</span>
                  </div>
                </div>
              </DialogContent>
              </Dialog>
            </TooltipProvider>
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-6 p-0 relative" ref={chartRef}>
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.7, ease: "easeOut" }}
          className="bg-card/40 backdrop-blur-md p-6 rounded-b-xl border-t border-cyan-500/10 hover:border-cyan-500/30 hover:shadow-[0_0_30px_rgba(34,211,238,0.15)] transition-all duration-300"
        >
          <div className="mb-4 hidden export-only text-foreground">
             <h2 className="text-xl font-bold">{artifact.metadata?.title || artifact.title}</h2>
             {artifact.metadata?.subtitle && <p className="text-sm text-muted-foreground">{artifact.metadata.subtitle}</p>}
          </div>

          {/* Render KPIs for inline view if available */}
          {artifact.insights?.kpi_cards?.length ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              {artifact.insights.kpi_cards.map((kpi, idx) => (
                <div key={idx} className="bg-background/40 backdrop-blur-sm p-4 rounded-xl border border-cyan-500/20 shadow-glow flex flex-col justify-center">
                  <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">{kpi.label}</p>
                  <p className="text-xl font-bold text-cyan-400 tracking-tight mt-1">{kpi.value}</p>
                </div>
              ))}
            </div>
          ) : null}

          <div className="h-[400px]">
            {renderChart()}
          </div>
        </motion.div>
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
