"use client";

import { useState } from "react";
import type { DecisionExplanation } from "../types";

interface Props {
  explanations: DecisionExplanation[];
}

function ExplanationCard({ exp, index }: { exp: DecisionExplanation; index: number }) {
  const [open, setOpen] = useState(index === 0);

  return (
    <div className="rounded-lg border border-zinc-800 overflow-hidden">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-zinc-800/50 transition-colors"
      >
        <div className="flex items-center gap-3 min-w-0">
          <span className="shrink-0 flex h-5 w-5 items-center justify-center rounded-full bg-indigo-600/20 text-[10px] font-bold text-indigo-400">
            {index + 1}
          </span>
          <span className="text-sm font-medium text-zinc-100 truncate">
            {exp.title}
          </span>
        </div>
        <div className="flex items-center gap-2 shrink-0 ml-2">
          {exp.constraint_satisfied && (
            <span className="hidden sm:inline-block text-[10px] px-2 py-0.5 rounded-full bg-violet-500/20 text-violet-400 border border-violet-500/20">
              {exp.constraint_satisfied}
            </span>
          )}
          <span className={`text-xs text-zinc-600 transition-transform ${open ? "rotate-90" : ""}`}>
            ▶
          </span>
        </div>
      </button>

      {open && (
        <div className="px-4 py-3 border-t border-zinc-800 space-y-3">
          <p className="text-sm text-zinc-300 leading-relaxed">{exp.reasoning}</p>

          {exp.alternatives_considered?.length > 0 && (
            <div>
              <p className="text-[10px] uppercase tracking-widest text-zinc-600 mb-1">
                Alternatives considered
              </p>
              <ul className="space-y-1">
                {exp.alternatives_considered.map((alt, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-zinc-500">
                    <span className="shrink-0 mt-1 h-1 w-1 rounded-full bg-zinc-600" />
                    {alt}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function DecisionExplanationPanel({ explanations }: Props) {
  if (!explanations.length) return null;

  return (
    <div className="space-y-3">
      <h2 className="text-sm font-semibold uppercase tracking-widest text-zinc-400">
        Why These Decisions?
      </h2>
      <div className="space-y-2">
        {explanations.map((exp, i) => (
          <ExplanationCard key={i} exp={exp} index={i} />
        ))}
      </div>
    </div>
  );
}
