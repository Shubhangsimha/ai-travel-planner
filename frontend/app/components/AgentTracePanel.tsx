"use client";

import { useEffect, useRef } from "react";
import type { TraceEvent } from "../types";

const STATUS_STYLES: Record<string, string> = {
  started: "bg-blue-500/20 text-blue-300 border-blue-500/30",
  running: "bg-yellow-500/20 text-yellow-300 border-yellow-500/30",
  completed: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
  failed: "bg-red-500/20 text-red-300 border-red-500/30",
};

const AGENT_COLORS: Record<string, string> = {
  GoalParser: "text-violet-400",
  WorkerDispatcher: "text-indigo-400",
  WeatherWorker: "text-sky-400",
  AttractionsWorker: "text-teal-400",
  RestaurantWorker: "text-orange-400",
  CurrencyWorker: "text-yellow-400",
  FlightWorker: "text-blue-400",
  HotelWorker: "text-pink-400",
  PlanSynthesizer: "text-emerald-400",
  CritiqueOptimizer: "text-red-400",
  DecisionExplainer: "text-purple-400",
  Orchestrator: "text-white",
};

interface Props {
  events: TraceEvent[];
  isStreaming: boolean;
}

export default function AgentTracePanel({ events, isStreaming }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events.length]);

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-2 border-b border-zinc-800">
        <h2 className="text-xs font-semibold uppercase tracking-widest text-zinc-400">
          Agent Trace
        </h2>
        {isStreaming && (
          <span className="flex items-center gap-1.5 text-xs text-indigo-400">
            <span className="h-1.5 w-1.5 rounded-full bg-indigo-400 animate-pulse" />
            Live
          </span>
        )}
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1 font-mono text-xs">
        {events.length === 0 && !isStreaming && (
          <p className="text-zinc-600 text-center py-8">
            Waiting for pipeline to start…
          </p>
        )}

        {events.map((event, i) => {
          const agentColor = AGENT_COLORS[event.agent] ?? "text-zinc-300";
          const statusStyle =
            STATUS_STYLES[event.status] ?? "bg-zinc-700 text-zinc-300";

          return (
            <div
              key={`${event.agent}-${event.timestamp_ms ?? i}`}
              className="flex items-start gap-2 py-1 border-b border-zinc-800/50 last:border-0"
            >
              <span className={`shrink-0 font-semibold w-36 truncate ${agentColor}`}>
                {event.agent}
              </span>
              <span
                className={`shrink-0 px-1.5 py-0.5 rounded border text-[10px] uppercase tracking-wide ${statusStyle}`}
              >
                {event.status}
              </span>
              <span className="text-zinc-400 flex-1 min-w-0 break-words leading-relaxed">
                {event.message}
                {event.duration_ms != null && (
                  <span className="ml-1 text-zinc-600">
                    ({event.duration_ms}ms)
                  </span>
                )}
              </span>
            </div>
          );
        })}

        {isStreaming && (
          <div className="flex items-center gap-2 py-1 text-zinc-600">
            <span className="animate-pulse">▶</span>
            <span>Processing…</span>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
