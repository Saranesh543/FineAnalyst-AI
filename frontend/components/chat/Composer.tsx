"use client";

import { useState, FormEvent, useRef, useEffect, DragEvent } from "react";
import {
  Send,
  Loader2,
  Paperclip,
  Mic,
  ArrowUpRight,
  Square,
  File as FileIcon,
  X,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "../ui/tooltip";
import { useConversationStore } from "@/lib/store/conversation-store";

interface ComposerProps {
  onSend: (text: string) => void;
  onCancel?: () => void;
  isStreaming: boolean;
  className?: string;
}

export function Composer({
  onSend,
  onCancel,
  isStreaming,
  className = "",
}: ComposerProps) {
  const [text, setText] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const activeSessionId = useConversationStore(
    (state) => state.activeSessionId,
  );
  const sessions = useConversationStore((state) => state.sessions);
  const uploadFile = useConversationStore((state) => state.uploadFile);
  const removeFile = useConversationStore((state) => state.removeFile);

  const stagedAttachments = useConversationStore(
    (state) => state.stagedAttachments,
  );
  const attachments = stagedAttachments || [];

  useEffect(() => {
    if (!isStreaming && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isStreaming]);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (isStreaming) return;
    if (text.trim() || attachments.length > 0) {
      onSend(text.trim() || "Analyze this uploaded file.");
      setText("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (isStreaming) return;
      handleSubmit(e as any);
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    for (const file of files) {
      await uploadFile(file);
    }
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleDragOver = (e: DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = async (e: DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files || []);
    for (const file of files) {
      await uploadFile(file);
    }
  };

  return (
    <div className={`w-full max-w-3xl mx-auto ${className}`}>
      <form
        onSubmit={handleSubmit}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`relative flex flex-col justify-between bg-card/20 backdrop-blur-xl rounded-[2rem] border transition-all min-h-[140px] ${
          isDragging
            ? "border-cyan-400 bg-cyan-950/20 shadow-[0_0_30px_rgba(34,211,238,0.3)]"
            : "border-cyan-500/20 shadow-glow focus-within:ring-1 focus-within:ring-cyan-500/50 focus-within:shadow-[0_0_30px_rgba(34,211,238,0.15)]"
        }`}
      >
        {isDragging && (
          <div className="absolute inset-0 z-10 flex items-center justify-center rounded-[2rem] bg-background/60 backdrop-blur-sm border-2 border-dashed border-cyan-400">
            <div className="flex flex-col items-center gap-2 text-cyan-400">
              <Paperclip className="h-8 w-8 animate-bounce" />
              <p className="font-medium text-lg">Drop files to attach</p>
            </div>
          </div>
        )}

        {attachments.length > 0 && (
          <div className="flex flex-wrap gap-2 px-6 pt-4">
            {attachments.map((file) => (
              <div
                key={file.id}
                className="flex items-center gap-2 bg-background/50 border border-border rounded-xl px-3 py-1.5 text-sm group relative"
              >
                <FileIcon className="h-4 w-4 text-cyan-500" />
                <span className="max-w-[120px] truncate text-foreground/80">
                  {file.filename}
                </span>
                {file.status === "uploading" && (
                  <Loader2 className="h-3 w-3 animate-spin text-cyan-500" />
                )}
                {file.status === "done" && (
                  <CheckCircle2 className="h-3 w-3 text-green-500" />
                )}
                {file.status === "error" && (
                  <AlertCircle className="h-3 w-3 text-red-500" />
                )}
                <button
                  type="button"
                  onClick={() => removeFile(file.id)}
                  className="absolute -top-1.5 -right-1.5 bg-background border border-border rounded-full p-0.5 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-destructive hover:text-destructive-foreground hover:border-destructive"
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
            ))}
          </div>
        )}

        <textarea
          ref={inputRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="What would you like to analyze today?"
          className={`w-full h-full resize-none bg-transparent px-6 pb-2 outline-none disabled:opacity-50 text-foreground text-lg placeholder:text-muted-foreground/70 ${attachments.length > 0 ? "pt-2" : "pt-6"}`}
          rows={1}
        />

        <input
          type="file"
          ref={fileInputRef}
          hidden
          onChange={handleFileChange}
          multiple
          accept=".csv,.xlsx,.xls,.sqlite,.db,.pdf,.docx,.txt,.json,image/*"
        />

        <div className="flex items-center justify-between px-2 md:px-4 pb-2">
          <Button
            type="button"
            variant="ghost"
            className="rounded-full text-muted-foreground hover:text-foreground gap-1 md:gap-2 ml-1 md:ml-2 mb-1"
            onClick={() => fileInputRef.current?.click()}
          >
            <Paperclip className="h-5 w-5" />
            <span className="text-xs md:text-sm font-medium">Attach</span>
          </Button>

          <div className="flex items-center gap-2">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  type="button"
                  size="icon"
                  variant="ghost"
                  disabled
                  className="rounded-full text-muted-foreground hover:text-foreground cursor-not-allowed opacity-50"
                >
                  <Mic className="h-5 w-5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Coming Soon</TooltipContent>
            </Tooltip>
            {isStreaming ? (
              <Button
                type="button"
                size="icon"
                onClick={onCancel}
                className="rounded-full h-12 w-12 shrink-0 bg-red-500 hover:bg-red-400 text-white shadow-[0_0_15px_rgba(239,68,68,0.4)] mb-1 mr-1"
              >
                <Square className="h-5 w-5 fill-current" />
              </Button>
            ) : (
              <Button
                type="submit"
                size="icon"
                disabled={!text.trim() && attachments.length === 0}
                className="rounded-full h-12 w-12 shrink-0 bg-cyan-400 hover:bg-cyan-300 text-black shadow-[0_0_15px_rgba(34,211,238,0.4)] disabled:opacity-50 disabled:shadow-none mb-1 mr-1"
              >
                <ArrowUpRight className="h-6 w-6" />
              </Button>
            )}
          </div>
        </div>
      </form>
    </div>
  );
}
