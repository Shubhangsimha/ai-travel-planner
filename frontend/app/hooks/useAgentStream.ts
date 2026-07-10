"use client";

import { useCallback, useRef, useState } from "react";
import type { TraceEvent, PlanResult, SSEMessage } from "../types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface StreamState {
  traceEvents: TraceEvent[];
  result: PlanResult | null;
  error: string | null;
  isStreaming: boolean;
}

export function useAgentStream() {
  const [state, setState] = useState<StreamState>({
    traceEvents: [],
    result: null,
    error: null,
    isStreaming: false,
  });

  const esRef = useRef<EventSource | null>(null);

  const startPlanning = useCallback(async (rawInput: string) => {
    // Reset state
    setState({ traceEvents: [], result: null, error: null, isStreaming: true });

    // Close any existing stream
    esRef.current?.close();

    try {
      // 1. Submit the plan request
      const res = await fetch(`${API_BASE}/api/plan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ raw_input: rawInput }),
      });

      if (!res.ok) throw new Error(`Plan request failed: ${res.status}`);

      const { session_id } = await res.json();

      // 2. Open SSE stream
      const es = new EventSource(`${API_BASE}/api/stream/${session_id}`);
      esRef.current = es;

      es.onmessage = (event) => {
        const msg: SSEMessage = JSON.parse(event.data);

        if (msg.type === "trace") {
          const { type: _, ...traceEvent } = msg;
          setState((prev) => ({
            ...prev,
            traceEvents: [...prev.traceEvents, traceEvent as TraceEvent],
          }));
        } else if (msg.type === "complete") {
          const { type: _, ...planResult } = msg;
          setState((prev) => ({
            ...prev,
            result: planResult as PlanResult,
            isStreaming: false,
          }));
          es.close();
        } else if (msg.type === "error") {
          setState((prev) => ({
            ...prev,
            error: msg.message,
            isStreaming: false,
          }));
          es.close();
        }
      };

      es.onerror = () => {
        setState((prev) => ({
          ...prev,
          error: "Stream connection lost. The server may still be processing.",
          isStreaming: false,
        }));
        es.close();
      };
    } catch (err) {
      setState((prev) => ({
        ...prev,
        error: err instanceof Error ? err.message : "Unknown error",
        isStreaming: false,
      }));
    }
  }, []);

  const reset = useCallback(() => {
    esRef.current?.close();
    setState({ traceEvents: [], result: null, error: null, isStreaming: false });
  }, []);

  return { ...state, startPlanning, reset };
}
