"use client";

import React, { useRef, useState } from "react";
import { EvidenceArtifact } from "@/lib/types/chat";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import * as htmlToImage from "html-to-image";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Loader2, Database, Check, Copy, Sparkles, X } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogClose,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { motion } from "framer-motion";

import { KpiCard } from "./charts/KpiCard";
import { BarChartWidget } from "./charts/BarChartWidget";
import { LineChartWidget } from "./charts/LineChartWidget";
import { AreaChartWidget } from "./charts/AreaChartWidget";
import { PieChartWidget } from "./charts/PieChartWidget";
import { ScatterChartWidget } from "./charts/ScatterChartWidget";
import { TreemapWidget } from "./charts/TreemapWidget";
import { MapPlaceholderWidget } from "./charts/MapPlaceholderWidget";
import { DataGridWidget } from "./charts/DataGridWidget";
import dynamic from "next/dynamic";
const MermaidWidget = dynamic(
  () => import("./MermaidWidget").then((mod) => mod.MermaidWidget),
  { ssr: false },
);
import { MermaidArtifactRenderer } from "./MermaidArtifactRenderer";
import { SqlViewer } from "./SqlViewer";
import { AiExecutiveSummary } from "./insights/AiExecutiveSummary";
import { BusinessRecommendations } from "./insights/BusinessRecommendations";
import { AiInsightSidebar } from "./insights/AiInsightSidebar";

function EvidenceCard({ artifact }: { artifact: EvidenceArtifact }) {
  const chartRef = useRef<HTMLDivElement>(null);
  const [copiedSQL, setCopiedSQL] = useState(false);
  const [downloadingPNG, setDownloadingPNG] = useState(false);

  let xKey = artifact.metadata?.x_axis || artifact.encoding?.x;
  let yKey = artifact.metadata?.y_axis || artifact.encoding?.y;

  // STRICT MODE: Rely only on metadata. No fallback guessing.

  const chartType =
    artifact.metadata?.chart_type || artifact.chartType || "data_grid";

  // Sanitize data to prevent Recharts from overwriting points with identical xKey values
  let safeData = artifact.data;
  if (
    safeData &&
    safeData.length > 0 &&
    xKey &&
    ["line", "bar", "area", "scatter"].includes(chartType)
  ) {
    const xValues = new Set();
    let requiresUniqueing = false;
    for (const row of safeData) {
      if (xValues.has(row[xKey])) {
        requiresUniqueing = true;
        break;
      }
      xValues.add(row[xKey]);
    }
    if (requiresUniqueing) {
      safeData = safeData.map((row, idx) => ({
        ...row,
        [xKey!]: `${row[xKey]} (${idx + 1})`,
      }));
    }
  }

  console.log(
    `[TRACE] EvidenceArtifactRenderer Props: analysisId=${artifact.analysisId || artifact.id}, chartType=${chartType}, title=${artifact.title}, data.length=${artifact.data?.length}, xKey=${xKey}, yKey=${yKey}, metadata=${JSON.stringify(artifact.metadata)}`,
  );

  // Diagnostics
  if (artifact.data && artifact.data.length > 0 && yKey) {
    let chartRevenueSum = 0;
    artifact.data.forEach((d) => {
      if (typeof d[yKey!] === "number") {
        chartRevenueSum += d[yKey!];
      } else if (typeof d[yKey!] === "string" && !isNaN(parseFloat(d[yKey!]))) {
        chartRevenueSum += parseFloat(d[yKey!]);
      }
    });

    // Attempt to extract the KPI total revenue from the insights
    let kpiTotal = 0;
    if (artifact.insights?.kpi_cards) {
      const revenueCard = artifact.insights.kpi_cards.find(
        (c) =>
          c.label.toLowerCase().includes("revenue") ||
          c.label.toLowerCase().includes("total"),
      );
      if (revenueCard && typeof revenueCard.value === "number") {
        kpiTotal = revenueCard.value;
      } else if (
        revenueCard &&
        typeof revenueCard.value === "string" &&
        !isNaN(parseFloat(revenueCard.value.replace(/[^0-9.-]+/g, "")))
      ) {
        kpiTotal = parseFloat(revenueCard.value.replace(/[^0-9.-]+/g, ""));
      }
    }

    const difference = Math.abs(kpiTotal - chartRevenueSum);

    console.log(
      `[Analytics] Result rows: ${artifact.rowCountTotal || artifact.data.length}`,
    );
    console.log(`[Analytics] Chart rows: ${artifact.data.length}`);
    console.log(`[Analytics] KPI total revenue: ${kpiTotal}`);
    console.log(`[Analytics] Chart revenue sum: ${chartRevenueSum}`);
    console.log(`[Analytics] Revenue difference: ${difference}`);
  }

  // Instrument logging as requested
  if (process.env.NODE_ENV === "development") {
    console.log("Chart Metadata Debug:", {
      analysisId: artifact.analysisId || artifact.id,
      chart_type: chartType,
      title: artifact.metadata?.title,
      subtitle: artifact.metadata?.subtitle,
      x_axis: xKey,
      y_axis: yKey,
      number_format: artifact.metadata?.number_format,
      confidence: artifact.metadata?.confidence || artifact.confidenceScore,
    });
  }

  const downloadCSV = () => {
    if (!artifact.data || artifact.data.length === 0) return;
    const headers = Object.keys(artifact.data[0]).join(",");
    const rows = artifact.data
      .map((row) =>
        Object.values(row)
          .map((val) => `"${val}"`)
          .join(","),
      )
      .join("\n");
    const csv = `${headers}\n${rows}`;
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${artifact.metadata?.title || "export"}.csv`
      .toLowerCase()
      .replace(/\s+/g, "_");
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const downloadPNG = () => {
    if (chartRef.current) {
      setDownloadingPNG(true);
      htmlToImage
        .toPng(chartRef.current, { backgroundColor: "#ffffff" })
        .then(function (dataUrl) {
          const a = document.createElement("a");
          a.href = dataUrl;
          a.download = `${artifact.metadata?.title || "chart"}.png`
            .toLowerCase()
            .replace(/\s+/g, "_");
          a.click();
        })
        .catch(function (error) {
          console.error("oops, something went wrong!", error);
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

  const formatSQL = (rawSql?: string) => {
    if (!rawSql) return "";
    if (rawSql.split("\n").length > 2) return rawSql;

    return rawSql
      .replace(
        /\s+(FROM|WHERE|GROUP BY|ORDER BY|LIMIT|HAVING|JOIN|LEFT JOIN|RIGHT JOIN|INNER JOIN)\s+/gi,
        "\n$1 ",
      )
      .replace(/^(SELECT)\s+/i, "$1\n    ")
      .replace(/,\s*/g, ",\n    ");
  };

  let yKeys =
    typeof yKey === "string" && yKey.includes(",")
      ? yKey.split(",").map((s) => s.trim())
      : yKey
        ? [yKey]
        : [];

  const renderChart = () => {
    if (!artifact.data || artifact.data.length === 0) {
      return (
        <div className="h-[300px] flex items-center justify-center text-muted-foreground bg-muted/10 rounded-lg border">
          No visualization available.
        </div>
      );
    }

    const needsAxes = !["kpi", "data_grid", "map"].includes(chartType);
    if (needsAxes && (!xKey || yKeys.length === 0)) {
      return (
        <div className="h-[300px] flex flex-col items-center justify-center text-muted-foreground bg-muted/10 rounded-lg border">
          <Database className="h-8 w-8 text-muted-foreground/50 mb-2" />
          <p>Visualization unavailable</p>
          <p className="text-xs text-muted-foreground mt-1">
            Unable to render this visualization due to missing axis data.
          </p>
        </div>
      );
    }

    const safeArtifact = { ...artifact, data: safeData };

    switch (chartType) {
      case "kpi":
        return <KpiCard artifact={safeArtifact} xKey={xKey!} yKey={yKeys[0]} />;
      case "bar":
        return (
          <BarChartWidget artifact={safeArtifact} xKey={xKey!} yKeys={yKeys} />
        );
      case "horizontal_bar":
        return (
          <BarChartWidget
            artifact={safeArtifact}
            xKey={xKey!}
            yKeys={yKeys}
            isHorizontal={true}
          />
        );
      case "line":
        return (
          <LineChartWidget artifact={safeArtifact} xKey={xKey!} yKeys={yKeys} />
        );
      case "area":
        return (
          <AreaChartWidget artifact={safeArtifact} xKey={xKey!} yKeys={yKeys} />
        );
      case "pie":
        return (
          <PieChartWidget
            artifact={safeArtifact}
            xKey={xKey!}
            yKey={yKeys[0]}
          />
        );
      case "donut":
        return (
          <PieChartWidget
            artifact={safeArtifact}
            xKey={xKey!}
            yKey={yKeys[0]}
            isDonut={true}
          />
        );
      case "scatter":
        return (
          <ScatterChartWidget
            artifact={safeArtifact}
            xKey={xKey!}
            yKey={yKeys[0]}
          />
        );
      case "treemap":
        return (
          <TreemapWidget artifact={safeArtifact} xKey={xKey!} yKey={yKeys[0]} />
        );
      case "map":
        return (
          <MapPlaceholderWidget
            artifact={safeArtifact}
            xKey={xKey!}
            yKeys={yKeys}
          />
        );
      case "mermaid":
        return (
          <MermaidWidget
            code={safeArtifact.metadata?.mermaid_code}
            title={safeArtifact.metadata?.title}
          />
        );
      case "data_grid":
        return <DataGridWidget artifact={safeArtifact} />;
      default:
        return <DataGridWidget artifact={safeArtifact} />;
    }
  };

  return (
    <Card className="shadow-sm">
      <CardHeader className="bg-muted/20 pb-4 border-b">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex flex-col">
            <div className="flex items-center space-x-2">
              <Database className="h-5 w-5 text-primary" />
              <CardTitle className="text-lg">
                {artifact.metadata?.title || artifact.title}
              </CardTitle>
            </div>
            {artifact.metadata?.subtitle && (
              <p className="text-sm text-muted-foreground mt-1 ml-7">
                {artifact.metadata.subtitle}
              </p>
            )}
          </div>
          <div className="flex items-center space-x-2">
            <TooltipProvider>
              {/* SQL Dialog */}
              <Dialog>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <DialogTrigger asChild>
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-8 text-xs font-semibold"
                      >
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
                    <pre className="p-4 bg-muted rounded-md overflow-x-auto overflow-y-auto max-h-[60vh] text-sm text-foreground whitespace-pre">
                      <code>{formatSQL(artifact.sql)}</code>
                    </pre>
                    <Button
                      variant="secondary"
                      size="sm"
                      className="absolute top-2 right-2"
                      onClick={copySQL}
                    >
                      {copiedSQL ? (
                        <Check className="h-4 w-4 mr-1 text-green-600" />
                      ) : (
                        <Copy className="h-4 w-4 mr-1" />
                      )}
                      {copiedSQL ? "Copied" : "Copy"}
                    </Button>
                  </div>
                </DialogContent>
              </Dialog>

              {/* CSV Download */}
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-8 text-xs font-semibold"
                    onClick={downloadCSV}
                    disabled={!artifact.data?.length}
                  >
                    <span className="mr-1">⬇</span> CSV
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Download raw data</TooltipContent>
              </Tooltip>

              {/* PNG Download */}
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-8 text-xs font-semibold"
                    onClick={downloadPNG}
                    disabled={downloadingPNG || !artifact.data?.length}
                  >
                    {downloadingPNG ? (
                      <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                    ) : (
                      <span className="mr-1">🖼</span>
                    )}{" "}
                    PNG
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Download chart image</TooltipContent>
              </Tooltip>

              {/* Expand Dialog */}
              <Dialog>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <DialogTrigger asChild>
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-8 text-xs font-semibold"
                      >
                        <span className="mr-1">⛶</span> Expand
                      </Button>
                    </DialogTrigger>
                  </TooltipTrigger>
                  <TooltipContent>Open fullscreen report</TooltipContent>
                </Tooltip>
                <DialogContent
                  showCloseButton={false}
                  className="sm:max-w-[95vw] lg:max-w-[95vw] xl:max-w-[1600px] w-full max-h-[100dvh] md:max-h-[95vh] h-[100dvh] md:h-[95vh] flex flex-col p-0 overflow-hidden bg-background/95 backdrop-blur-3xl border-cyan-500/30 shadow-[0_0_50px_rgba(34,211,238,0.15)] rounded-none md:rounded-2xl"
                >
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
                            {chartType.replace("_", " ")}
                          </span>
                        </DialogTitle>
                        <p className="text-sm text-muted-foreground mt-0.5 flex items-center space-x-2">
                          <span>
                            Database:{" "}
                            <span className="text-foreground/80 font-medium">
                              FineAnalyst Demo
                            </span>
                          </span>
                          <span>•</span>
                          <span>
                            Generated: {new Date().toLocaleDateString()}{" "}
                            {new Date().toLocaleTimeString([], {
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </span>
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Button
                        variant="outline"
                        size="sm"
                        className="hidden md:flex h-9 bg-black/20 border-white/10 hover:bg-white/10"
                        onClick={downloadCSV}
                        disabled={!artifact.data?.length}
                      >
                        <span className="mr-2">⬇</span> Export CSV
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="hidden md:flex h-9 bg-black/20 border-white/10 hover:bg-white/10"
                        onClick={downloadPNG}
                        disabled={downloadingPNG || !artifact.data?.length}
                      >
                        {downloadingPNG ? (
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        ) : (
                          <span className="mr-2">🖼</span>
                        )}{" "}
                        Export Image
                      </Button>
                      <div className="w-px h-6 bg-white/10 mx-2" />
                      <DialogClose asChild>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-9 w-9 rounded-full hover:bg-white/10 text-muted-foreground hover:text-foreground transition-colors shrink-0"
                        >
                          <X className="h-5 w-5" />
                          <span className="sr-only">Close</span>
                        </Button>
                      </DialogClose>
                    </div>
                  </DialogHeader>

                  {/* Body */}
                  <div className="flex-1 overflow-y-auto custom-scrollbar bg-background/40 relative">
                    <div className="p-6 md:p-8 space-y-8 max-w-[1600px] mx-auto">
                      {/* KPIs */}
                      {artifact.insights?.kpi_cards?.length ? (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 animate-in slide-in-from-bottom-4 duration-500">
                          {artifact.insights.kpi_cards.map((kpi, idx) => (
                            <div
                              key={idx}
                              className="bg-card/40 backdrop-blur-md p-5 rounded-2xl border border-cyan-500/10 shadow-glow transition-all hover:-translate-y-1 hover:border-cyan-500/30 hover:shadow-[0_0_30px_rgba(34,211,238,0.15)] group flex flex-col justify-between h-32"
                            >
                              <div className="flex justify-between items-start">
                                <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider group-hover:text-cyan-400/80 transition-colors">
                                  {kpi.label}
                                </p>
                              </div>
                              <p className="text-4xl font-bold text-cyan-400 tracking-tight">
                                {kpi.value}
                              </p>
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
                            {chartType !== "data_grid" && (
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
                          <AiExecutiveSummary
                            insights={artifact.insights || {}}
                          />
                          <BusinessRecommendations
                            recommendations={
                              artifact.insights?.recommendations || []
                            }
                          />
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Footer */}
                  <div className="sticky bottom-0 z-20 shrink-0 bg-background/95 backdrop-blur-xl px-6 py-3 border-t border-white/5 flex items-center justify-between text-xs text-muted-foreground">
                    <div className="flex items-center space-x-4">
                      <span>
                        Rows Returned:{" "}
                        <strong className="text-foreground">
                          {artifact.rowCountTotal || artifact.data?.length || 0}
                        </strong>
                      </span>
                      <span>•</span>
                      <span>
                        Execution Time:{" "}
                        <strong className="text-foreground">312ms</strong>
                      </span>
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
            <h2 className="text-xl font-bold">
              {artifact.metadata?.title || artifact.title}
            </h2>
            {artifact.metadata?.subtitle && (
              <p className="text-sm text-muted-foreground">
                {artifact.metadata.subtitle}
              </p>
            )}
          </div>

          {/* Render KPIs for inline view if available */}
          {artifact.insights?.kpi_cards?.length ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              {artifact.insights.kpi_cards.map((kpi, idx) => (
                <div
                  key={idx}
                  className="bg-background/40 backdrop-blur-sm p-4 rounded-xl border border-cyan-500/20 shadow-glow flex flex-col justify-center"
                >
                  <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
                    {kpi.label}
                  </p>
                  <p className="text-xl font-bold text-cyan-400 tracking-tight mt-1">
                    {kpi.value}
                  </p>
                </div>
              ))}
            </div>
          ) : null}

          <div className="h-[400px] w-full overflow-x-auto overflow-y-hidden custom-scrollbar">
            <div className="min-w-[600px] md:min-w-0 h-full">
              {renderChart()}
            </div>
          </div>
        </motion.div>
      </CardContent>
    </Card>
  );
}

export function EvidenceArtifactRenderer({
  evidence,
}: {
  evidence: EvidenceArtifact[];
}) {
  if (!evidence || evidence.length === 0) return null;

  return (
    <div className="flex flex-col space-y-8 mt-8 border-t pt-8">
      {evidence.map((artifact) => (
        <div key={artifact.id}>
          {artifact.kind === "mermaid" ? (
            <MermaidArtifactRenderer artifact={artifact} />
          ) : (
            <EvidenceCard artifact={artifact} />
          )}
        </div>
      ))}
    </div>
  );
}
