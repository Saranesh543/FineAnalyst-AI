"use client";

import { useState, FormEvent, useRef, useEffect } from "react";
import { Send, Loader2, Paperclip, Mic, ArrowUpRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "../ui/tooltip";

interface ComposerProps {
  onSend: (text: string) => void;
  isStreaming: boolean;
  className?: string;
}

export function Composer({ onSend, isStreaming, className = "" }: ComposerProps) {
  const [text, setText] = useState("");
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!isStreaming && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isStreaming]);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    console.log(`[Composer] handleSubmit triggered. text="${text}", isStreaming=${isStreaming}`);
    if (text.trim() && !isStreaming) {
      console.log(`[Composer] Calling onSend for text: "${text.trim()}"`);
      onSend(text.trim());
      setText("");
    } else {
      console.log(`[Composer] Submission skipped. isStreaming=${isStreaming}, text.trim()=${!!text.trim()}`);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as any);
    }
  };

  return (
    <div className={`w-full max-w-3xl mx-auto ${className}`}>
      <form onSubmit={handleSubmit} className="relative flex flex-col justify-between bg-card/20 backdrop-blur-xl rounded-[2rem] border border-cyan-500/20 shadow-glow p-2 focus-within:ring-1 focus-within:ring-cyan-500/50 focus-within:shadow-[0_0_30px_rgba(34,211,238,0.15)] transition-all min-h-[140px]">
        <textarea
          ref={inputRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="What would you like to analyze today?"
          disabled={isStreaming}
          className="w-full h-full resize-none bg-transparent px-6 pt-6 pb-2 outline-none disabled:opacity-50 text-foreground text-lg placeholder:text-muted-foreground/70"
          rows={1}
        />
        <div className="flex items-center justify-between px-2 pb-2">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button type="button" variant="ghost" disabled className="rounded-full text-muted-foreground hover:text-foreground gap-2 cursor-not-allowed opacity-50 ml-2 mb-1">
                <Paperclip className="h-5 w-5" />
                <span className="text-sm font-medium">Attach file</span>
              </Button>
            </TooltipTrigger>
            <TooltipContent>Coming Soon</TooltipContent>
          </Tooltip>
          
          <div className="flex items-center gap-2">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button type="button" size="icon" variant="ghost" disabled className="rounded-full text-muted-foreground hover:text-foreground cursor-not-allowed opacity-50">
                  <Mic className="h-5 w-5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Coming Soon</TooltipContent>
            </Tooltip>
            <Button 
              type="submit" 
              size="icon" 
              disabled={!text.trim() || isStreaming}
              className="rounded-full h-12 w-12 shrink-0 bg-cyan-400 hover:bg-cyan-300 text-black shadow-[0_0_15px_rgba(34,211,238,0.4)] disabled:opacity-50 disabled:shadow-none mb-1 mr-1"
            >
              {isStreaming ? <Loader2 className="h-6 w-6 animate-spin" /> : <ArrowUpRight className="h-6 w-6" />}
            </Button>
          </div>
        </div>
      </form>
    </div>
  );
}
