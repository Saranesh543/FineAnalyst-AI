"use client";

import { useCallback, useMemo } from "react";
import useSWR from "swr";

// UIArtifact stub — FineAnalyst renders artifacts via custom evidence components.
export type UIArtifact = {
  documentId: string;
  content: string;
  kind: "text" | "code" | "sheet";
  title: string;
  status: "idle" | "streaming";
  isVisible: boolean;
  boundingBox: { top: number; left: number; width: number; height: number };
};

export const initialArtifactData: UIArtifact = {
  boundingBox: {
    height: 0,
    left: 0,
    top: 0,
    width: 0,
  },
  content: "",
  documentId: "init",
  isVisible: false,
  kind: "text",
  status: "idle",
  title: "",
};

type Selector<T> = (state: UIArtifact) => T;

export function useArtifactSelector<Selected>(selector: Selector<Selected>) {
  const { data: localArtifact } = useSWR<UIArtifact>("artifact", null, {
    fallbackData: initialArtifactData,
  });

  const selectedValue = useMemo(() => {
    if (!localArtifact) {
      return selector(initialArtifactData);
    }
    return selector(localArtifact);
  }, [localArtifact, selector]);

  return selectedValue;
}

export function useArtifact() {
  const { data: localArtifact, mutate: setLocalArtifact } = useSWR<UIArtifact>(
    "artifact",
    null,
    {
      fallbackData: initialArtifactData,
    }
  );

  const artifact = useMemo(() => {
    if (!localArtifact) {
      return initialArtifactData;
    }
    return localArtifact;
  }, [localArtifact]);

  const setArtifact = useCallback(
    (updaterFn: UIArtifact | ((currentArtifact: UIArtifact) => UIArtifact)) => {
      setLocalArtifact((currentArtifact: UIArtifact | undefined) => {
        const artifactToUpdate = currentArtifact || initialArtifactData;

        if (typeof updaterFn === "function") {
          return updaterFn(artifactToUpdate);
        }

        return updaterFn;
      });
    },
    [setLocalArtifact]
  );

  const { data: localArtifactMetadata, mutate: setLocalArtifactMetadata } =
    useSWR<any>(
      () =>
        artifact.documentId ? `artifact-metadata-${artifact.documentId}` : null,
      null,
      {
        fallbackData: null,
      }
    );

  return useMemo(
    () => ({
      artifact,
      metadata: localArtifactMetadata,
      setArtifact,
      setMetadata: setLocalArtifactMetadata,
    }),
    [artifact, setArtifact, localArtifactMetadata, setLocalArtifactMetadata]
  );
}
