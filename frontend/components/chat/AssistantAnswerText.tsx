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

export function AssistantAnswerText({ text, isStreaming }: AssistantAnswerTextProps) {
  const [displayedText, setDisplayedText] = useState("");

  useEffect(() => {
    if (!text) {
      setDisplayedText("");
      return;
    }
    
    // If we're getting text for the first time, type it out
    if (displayedText.length === 0 && text.length > 0) {
      let i = 0;
      const interval = setInterval(() => {
        if (i < text.length - 1) {
          setDisplayedText(text.slice(0, i + 1));
          i++;
        } else {
          setDisplayedText(text);
          clearInterval(interval);
        }
      }, 15); // Adjust typing speed here
      
      return () => clearInterval(interval);
    } else if (text !== displayedText && displayedText.length > 0 && text.length === displayedText.length) {
      // Just a safeguard in case it rerenders with same text
      setDisplayedText(text);
    }
  }, [text]);

  if (!text && isStreaming) {
    return <span className="text-muted-foreground animate-pulse">Thinking...</span>;
  }

  return (
    <div className="prose prose-sm md:prose-base dark:prose-invert max-w-none prose-p:leading-relaxed">
      <Streamdown 
        mode={displayedText.length < (text?.length || 0) || isStreaming ? "streaming" : "static"}
        plugins={{ code, math, mermaid }}
      >
        {displayedText || text || ""}
      </Streamdown>
    </div>
  );
}
