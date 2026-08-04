// This file is a stub — FineAnalyst does not use Vercel artifact persistence.
// All artifact rendering is handled via the FineAnalyst FastAPI backend.

export type ArtifactKind = "text" | "code" | "sheet";

export const artifactKinds = ["text", "code", "sheet"] as const;

// No-op exports to satisfy any remaining imports
export const documentHandlersByArtifactKind: unknown[] = [];
