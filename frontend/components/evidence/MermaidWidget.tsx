import React, { useEffect, useRef, useState } from "react";
import mermaid from "mermaid";
import { AlertCircle } from "lucide-react";

interface MermaidWidgetProps {
  code?: string;
  title?: string;
}

export function MermaidWidget({ code, title }: MermaidWidgetProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [svgContent, setSvgContent] = useState<string>("");

  useEffect(() => {
    let isMounted = true;
    
    if (!code) {
      setError("No Mermaid syntax provided.");
      return;
    }

    const renderMermaid = async () => {
      try {
        setError(null);
        mermaid.initialize({
          startOnLoad: false,
          theme: "default",
          securityLevel: "loose",
        });

        // Ensure unique ID for multiple charts
        const id = `mermaid-svg-${Math.round(Math.random() * 1000000)}`;
        const { svg } = await mermaid.render(id, code);
        
        if (isMounted) {
          setSvgContent(svg);
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err.message || "Failed to render Mermaid diagram.");
        }
      }
    };

    renderMermaid();

    return () => {
      isMounted = false;
    };
  }, [code]);

  if (error) {
    return (
      <div className="w-full h-full flex items-center justify-center p-4">
        <div className="max-w-md bg-destructive/15 text-destructive border-destructive/20 border rounded-lg p-4 flex flex-col gap-2">
          <div className="flex items-center gap-2 font-medium">
            <AlertCircle className="h-4 w-4" />
            <span>Diagram Error</span>
          </div>
          <div className="text-xs font-mono overflow-auto max-h-32 text-destructive/80">
            {error}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col w-full h-full">
      {title && (
        <div className="text-center font-medium text-sm text-muted-foreground mb-4">
          {title}
        </div>
      )}
      <div 
        ref={containerRef}
        className="flex-1 w-full flex items-center justify-center overflow-auto bg-white/50 dark:bg-black/20 rounded-md p-4"
        dangerouslySetInnerHTML={{ __html: svgContent }}
      />
    </div>
  );
}
