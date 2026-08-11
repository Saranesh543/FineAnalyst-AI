// RESOLUTION: 1. Streaming: Backend returns a single JSON response (no true streaming). 2. Intermediate tool-call steps: Not exposed, only final composed answer.
"use client";

import { useEffect, useState } from "react";
import { Streamdown } from "streamdown";
import { code } from "@streamdown/code";
import { math } from "@streamdown/math";
import { mermaid } from "@streamdown/mermaid";

interface AssistantAnswerTextProps {
  text?: string;
  isStreaming: boolean;
}

// ---------------------------------------------------------------------------
// Safe Shiki Wrapper
// ---------------------------------------------------------------------------
const ALIASES: Record<string, string> = {
  "py": "python",
  "js": "javascript",
  "ts": "typescript",
  "sh": "bash",
  "shell": "bash",
  "md": "markdown"
};

const safeCodePlugin = {
  ...code,
  highlight: (params: any, callback?: any) => {
    try {
      let lang = (params.language || "").toLowerCase().trim();
      
      // Normalize common aliases
      if (ALIASES[lang]) {
        lang = ALIASES[lang];
      }

      // Check if language is complete and supported
      const isSupported = typeof code.supportsLanguage === 'function' && code.supportsLanguage(lang);
      
      // If unsupported (e.g. streaming partial like "p" or "pyth")
      if (!isSupported) {
        lang = "text"; // Safe fallback to prevent Shiki from crashing
      }

      return code.highlight?.({ ...params, language: lang }, callback);
    } catch (e) {
      console.debug("[SafeCodePlugin] Suppressed highlighting error:", e);
      return null;
    }
  }
};
// ---------------------------------------------------------------------------

export function AssistantAnswerText({ text, isStreaming }: AssistantAnswerTextProps) {
  const [displayedText, setDisplayedText] = useState("");

  useEffect(() => {
    setDisplayedText(text || "");
  }, [text]);

  if (!text && isStreaming) {
    return <span className="text-muted-foreground animate-pulse">Thinking...</span>;
  }

  return (
    <div className="prose prose-sm md:prose-base dark:prose-invert max-w-none prose-p:leading-relaxed">
      <Streamdown 
        mode={displayedText.length < (text?.length || 0) || isStreaming ? "streaming" : "static"}
        plugins={{ code: safeCodePlugin, math, mermaid }}
      >
        {displayedText || text || ""}
      </Streamdown>
    </div>
  );
}
