import React, { useState } from "react";
import { EvidenceArtifact } from "@/lib/types/chat";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Maximize2, Code, FileCode2, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { MermaidWidget } from "./MermaidWidget";

interface MermaidArtifactRendererProps {
  artifact: EvidenceArtifact;
}

export function MermaidArtifactRenderer({ artifact }: MermaidArtifactRendererProps) {
  React.useEffect(() => {
    console.log("[MERMAID RENDER] Mounted MermaidArtifactRenderer for artifact:", artifact);
  }, [artifact]);

  const [showCode, setShowCode] = useState(false);

  const title = artifact.title || artifact.metadata?.title || "Mermaid Diagram";
  const code = artifact.mermaidCode || "";
  const error = artifact.mermaidError;

  return (
    <Card className="w-full bg-white dark:bg-black/40 overflow-hidden border shadow-sm">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-slate-700 dark:text-slate-300 flex items-center gap-2">
          <FileCode2 className="h-4 w-4 text-slate-500" />
          {title}
        </CardTitle>
        {!error && code && (
          <div className="flex gap-2">
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
              onClick={() => setShowCode(!showCode)}
              title={showCode ? "Hide Code" : "Show Code"}
            >
              <Code className="h-4 w-4" />
            </Button>
            <Dialog>
              <DialogTrigger asChild>
                <Button variant="ghost" size="icon" className="h-8 w-8 text-slate-500 hover:text-slate-700 dark:hover:text-slate-300" title="Expand Diagram">
                  <Maximize2 className="h-4 w-4" />
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-5xl w-[90vw] h-[85vh] flex flex-col">
                <DialogHeader>
                  <DialogTitle>{title}</DialogTitle>
                </DialogHeader>
                <div className="flex-1 overflow-auto bg-slate-50/50 dark:bg-slate-900/50 p-4 rounded-md">
                  <MermaidWidget code={code} />
                </div>
              </DialogContent>
            </Dialog>
          </div>
        )}
      </CardHeader>
      <CardContent className="p-0">
        {error ? (
          <div className="p-6 flex flex-col items-center justify-center text-center gap-3 text-slate-500 dark:text-slate-400">
            <div className="p-3 bg-red-50 dark:bg-red-900/20 rounded-full text-red-500">
              <AlertCircle className="h-6 w-6" />
            </div>
            <div>
              <p className="font-medium text-slate-700 dark:text-slate-300">Unable to generate diagram</p>
              <p className="text-sm max-w-sm mx-auto mt-1">{error}</p>
            </div>
          </div>
        ) : (
          <div className="flex flex-col">
            <div className="p-6 h-[400px] overflow-auto">
              <MermaidWidget code={code} />
            </div>
            {showCode && (
              <div className="border-t p-4 bg-slate-50 dark:bg-slate-900/50">
                <pre className="text-xs overflow-x-auto font-mono text-slate-600 dark:text-slate-400 p-2">
                  {code}
                </pre>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
