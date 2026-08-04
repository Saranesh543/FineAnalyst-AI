"use client";

import { useState, FormEvent, useRef, useEffect } from "react";
import { Send, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ComposerProps {
  onSend: (text: string) => void;
  isStreaming: boolean;
}

export function Composer({ onSend, isStreaming }: ComposerProps) {
  const [text, setText] = useState("");
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!isStreaming && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isStreaming]);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (text.trim() && !isStreaming) {
      onSend(text.trim());
      setText("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as any);
    }
  };

  return (
    <div className="w-full bg-background border-t p-4 pb-8 shadow-sm">
      <form onSubmit={handleSubmit} className="max-w-4xl mx-auto relative flex items-end bg-accent/30 rounded-2xl border p-2 focus-within:ring-1 focus-within:ring-primary transition-all">
        <textarea
          ref={inputRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question about your data..."
          disabled={isStreaming}
          className="w-full max-h-48 min-h-[52px] resize-none bg-transparent p-3 outline-none disabled:opacity-50"
          rows={1}
        />
        <Button 
          type="submit" 
          size="icon" 
          disabled={!text.trim() || isStreaming}
          className="mb-1 ml-2 rounded-xl h-10 w-10 shrink-0"
        >
          {isStreaming ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}
        </Button>
      </form>
      <div className="text-center mt-3 text-xs text-muted-foreground">
        AI can make mistakes. Verify important information.
      </div>
    </div>
  );
}
