"use client";

import { useEffect, useState } from "react";
import { agentClient, SchemaResponse } from "@/lib/api/agent-client";
import { MessageSquare } from "lucide-react";

interface EmptyStateProps {
  onSelectPrompt: (prompt: string) => void;
}

export function EmptyState({ onSelectPrompt }: EmptyStateProps) {
  const [schema, setSchema] = useState<SchemaResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    agentClient.getSchema()
      .then(setSchema)
      .catch(console.error)
      .finally(() => setIsLoading(false));
  }, []);

  let prompts = [
    "What are the top 5 products by revenue?",
    "Show me the sales trend over the last 12 months.",
    "Which region has the highest profit margin?"
  ];

  if (schema && schema.tables && schema.tables.length > 0) {
    const tableNames = schema.tables.map(t => t.name).slice(0, 3);
    prompts = [
      `How many records are in the ${tableNames[0] || 'users'} table?`,
      `Show me the latest entries in ${tableNames[1] || tableNames[0] || 'orders'}.`,
      `Summarize the data in ${tableNames[2] || tableNames[0] || 'products'}.`
    ];
  }

  return (
    <div className="flex flex-col items-center justify-center h-full p-8 text-center space-y-8 max-w-2xl mx-auto">
      <div className="space-y-4">
        <h1 className="text-4xl font-semibold tracking-tight">FineAnalyst AI</h1>
        <p className="text-muted-foreground text-lg">
          Ask questions about your data, generate insights, and visualize results instantly.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 w-full">
        {isLoading ? (
          <div className="col-span-3 text-muted-foreground">Loading schema for dynamic prompts...</div>
        ) : (
          prompts.map((prompt, idx) => (
            <button
              key={idx}
              onClick={() => onSelectPrompt(prompt)}
              className="p-4 flex flex-col items-start space-y-2 text-left rounded-xl border bg-card hover:bg-accent/50 transition-colors shadow-sm"
            >
              <MessageSquare className="h-5 w-5 text-primary/70" />
              <span className="text-sm font-medium">{prompt}</span>
            </button>
          ))
        )}
      </div>
    </div>
  );
}
