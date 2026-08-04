"use client";

import { EvidenceArtifact } from "@/lib/types/chat";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Code2, Database } from "lucide-react";
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

const COLORS = ['#2563eb', '#16a34a', '#dc2626', '#eab308', '#9333ea', '#0891b2'];

export function EvidenceArtifactRenderer({ evidence }: EvidenceArtifactRendererProps) {
  if (!evidence || evidence.length === 0) return null;

  return (
    <div className="flex flex-col space-y-6 mt-6 pt-6 border-t">
      {evidence.map((artifact) => {
        // If data is empty, just show a message
        if (!artifact.data || artifact.data.length === 0) {
          return (
            <Card key={artifact.id} className="overflow-hidden shadow-sm">
              <CardHeader className="bg-muted/30 pb-4 border-b">
                <CardTitle className="text-base">{artifact.title}</CardTitle>
              </CardHeader>
              <CardContent className="p-8 text-center text-muted-foreground text-sm">
                No data returned for this query.
              </CardContent>
            </Card>
          );
        }

        // Attempt to auto-detect x and y keys if not provided in encoding
        let xKey = artifact.encoding?.x;
        let yKey = artifact.encoding?.y;
        
        if (!xKey || !yKey) {
          const keys = Object.keys(artifact.data[0]);
          // Usually first string is X, first number is Y
          xKey = xKey || keys.find(k => typeof artifact.data[0][k] === 'string') || keys[0];
          yKey = yKey || keys.find(k => typeof artifact.data[0][k] === 'number') || keys[1] || keys[0];
        }

        const renderChart = () => {
          const type = artifact.chartType || 'bar';
          
          switch (type) {
            case 'line':
              return (
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={artifact.data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey={xKey} />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey={yKey} stroke="#2563eb" strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              );
            case 'pie':
              return (
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Tooltip />
                    <Legend />
                    <Pie
                      data={artifact.data}
                      dataKey={yKey!}
                      nameKey={xKey!}
                      cx="50%"
                      cy="50%"
                      outerRadius={100}
                      fill="#8884d8"
                      label
                    >
                      {artifact.data.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>
              );
            case 'scatter':
              return (
                <ResponsiveContainer width="100%" height={300}>
                  <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                    <CartesianGrid />
                    <XAxis type="number" dataKey={xKey} name={xKey} />
                    <YAxis type="number" dataKey={yKey} name={yKey} />
                    <Tooltip cursor={{ strokeDasharray: '3 3' }} />
                    <Scatter name={artifact.title} data={artifact.data} fill="#2563eb" />
                  </ScatterChart>
                </ResponsiveContainer>
              );
            case 'bar':
            default:
              return (
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={artifact.data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey={xKey} />
                    <YAxis />
                    <Tooltip cursor={{ fill: 'transparent' }} />
                    <Legend />
                    <Bar dataKey={yKey} fill="#2563eb" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              );
          }
        };

        return (
          <Card key={artifact.id} className="overflow-hidden shadow-sm">
            <CardHeader className="bg-muted/30 pb-4 border-b">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Database className="h-4 w-4 text-primary" />
                  <CardTitle className="text-base">{artifact.title}</CardTitle>
                </div>
                <div className="text-xs text-muted-foreground flex items-center space-x-1">
                  <span className="font-mono bg-muted px-1.5 py-0.5 rounded border">{artifact.rowCountTotal} rows</span>
                </div>
              </div>
              <CardDescription className="flex items-start mt-2 space-x-2">
                <Code2 className="h-3 w-3 mt-0.5 text-muted-foreground shrink-0" />
                <span className="font-mono text-xs break-all text-muted-foreground">{artifact.sql}</span>
              </CardDescription>
            </CardHeader>
            <CardContent className="p-4 pt-6">
              {renderChart()}
              <div className="text-center mt-4">
                <button className="text-xs text-muted-foreground hover:text-primary transition-colors underline underline-offset-2">
                  View full data table in Evidence Panel
                </button>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
