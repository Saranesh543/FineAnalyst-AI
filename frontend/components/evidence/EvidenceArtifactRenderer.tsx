"use client";

import React, { useRef, useState } from 'react';
import { EvidenceArtifact } from "@/lib/types/chat";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Database, Copy, Download, Maximize2, X, Check } from "lucide-react";
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogClose } from "@/components/ui/dialog";
import * as htmlToImage from 'html-to-image';

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

  let xKey = artifact.metadata?.x_axis || artifact.encoding?.x;
  let yKey = artifact.metadata?.y_axis || artifact.encoding?.y;
  
  if (!xKey || !yKey) {
    if (artifact.data && artifact.data.length > 0) {
      const keys = Object.keys(artifact.data[0]);
      xKey = xKey || keys.find(k => typeof artifact.data[0][k] === 'string') || keys[0];
      yKey = yKey || keys.find(k => typeof artifact.data[0][k] === 'number') || keys[1] || keys[0];
    }
  }

  const chartType = artifact.metadata?.chart_type || artifact.chartType || 'table';
  
  // Instrument logging as requested
  console.log("Chart Metadata Debug:", {
    chart_type: chartType,
    title: artifact.metadata?.title,
    subtitle: artifact.metadata?.subtitle,
    x_axis: xKey,
    y_axis: yKey,
    number_format: artifact.metadata?.number_format,
    confidence: artifact.metadata?.confidence || artifact.confidenceScore
  });

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
      htmlToImage.toPng(chartRef.current, { backgroundColor: '#ffffff' })
        .then(function (dataUrl) {
          const a = document.createElement('a');
          a.href = dataUrl;
          a.download = `${artifact.metadata?.title || 'chart'}.png`.toLowerCase().replace(/\s+/g, '_');
          a.click();
        })
        .catch(function (error) {
          console.error('oops, something went wrong!', error);
        });
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

    switch (chartType) {
      case 'kpi':
        return <KpiCard artifact={artifact} xKey={xKey!} yKey={yKey!} />;
      case 'bar':
        return <BarChartWidget artifact={artifact} xKey={xKey!} yKey={yKey!} />;
      case 'horizontal-bar':
        return <BarChartWidget artifact={artifact} xKey={xKey!} yKey={yKey!} isHorizontal={true} />;
      case 'line':
      case 'multi-line':
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
      case 'table':
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
            
            {/* SQL Dialog */}
            <Dialog>
              <DialogTrigger asChild>
                <Button variant="outline" size="sm" className="h-8 text-xs" title="View SQL">
                  <Copy className="h-3 w-3 mr-1" /> SQL
                </Button>
              </DialogTrigger>
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
            <Button variant="outline" size="sm" className="h-8 text-xs" title="Download CSV" onClick={downloadCSV}>
              <Download className="h-3 w-3 mr-1" /> CSV
            </Button>
            
            {/* PNG Download */}
            <Button variant="outline" size="sm" className="h-8 text-xs" title="Download PNG" onClick={downloadPNG}>
              <Download className="h-3 w-3 mr-1" /> PNG
            </Button>
            
            {/* Expand Dialog */}
            <Dialog>
              <DialogTrigger asChild>
                <Button variant="outline" size="sm" className="h-8 text-xs" title="Expand">
                  <Maximize2 className="h-3 w-3 mr-1" /> Expand
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-[90vw] w-[1200px] max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                  <div className="flex items-center space-x-2">
                    <Database className="h-6 w-6 text-primary" />
                    <DialogTitle className="text-xl">{artifact.metadata?.title || artifact.title}</DialogTitle>
                  </div>
                  {artifact.metadata?.subtitle && (
                    <p className="text-sm text-muted-foreground mt-1 ml-8">{artifact.metadata.subtitle}</p>
                  )}
                </DialogHeader>
                
                <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 mt-4">
                  <div className="lg:col-span-3 space-y-6">
                    <div className="bg-white p-6 rounded-lg border shadow-sm h-[500px]">
                      {renderChart()}
                    </div>
                    {/* Optionally DataGrid below chart in expanded view if not a datagrid already */}
                    {chartType !== 'data_grid' && chartType !== 'table' && (
                      <div className="mt-6">
                        <h3 className="font-semibold mb-2">Raw Data</h3>
                        <DataGridWidget artifact={artifact} />
                      </div>
                    )}
                  </div>
                  <div className="lg:col-span-1 space-y-6">
                    {artifact.insights?.kpi_cards?.map((kpi, idx) => (
                      <div key={idx} className="p-4 bg-muted/10 rounded-lg border">
                        <p className="text-sm text-muted-foreground uppercase">{kpi.label}</p>
                        <p className="text-3xl font-bold text-primary mt-1">{kpi.value}</p>
                      </div>
                    ))}
                    
                    {artifact.insights?.key_findings?.length ? (
                      <div className="space-y-2">
                        <h3 className="font-semibold border-b pb-2">Key Findings</h3>
                        <ul className="space-y-2 text-sm">
                          {artifact.insights.key_findings.map((f, i) => (
                            <li key={i} className="flex items-start">
                              <span className="mr-2 text-primary">•</span> {f}
                            </li>
                          ))}
                        </ul>
                      </div>
                    ) : null}
                    
                    {artifact.insights?.recommendations?.length ? (
                      <div className="space-y-2 mt-4">
                        <h3 className="font-semibold border-b pb-2">Recommendations</h3>
                        <ul className="space-y-2 text-sm">
                          {artifact.insights.recommendations.map((r, i) => (
                            <li key={i} className="flex items-start">
                              <span className="mr-2 text-primary">•</span> {r}
                            </li>
                          ))}
                        </ul>
                      </div>
                    ) : null}
                    
                    {artifact.confidenceScore && (
                      <div className="mt-4 pt-4 border-t">
                        <div className="flex items-center space-x-1">
                          <Check className="h-4 w-4 text-green-600" />
                          <span className="text-xs font-semibold text-green-700 bg-green-100 px-2 py-0.5 rounded-full">
                            {artifact.confidenceScore} Confidence
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </DialogContent>
            </Dialog>
          </div>
        </div>
      </CardHeader>
      {/* The ref is placed on CardContent so the PNG export captures just the chart context */}
      <CardContent className="pt-6" ref={chartRef}>
        <div className="bg-white p-4">
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
