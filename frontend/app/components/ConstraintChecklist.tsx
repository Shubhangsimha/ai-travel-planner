"use client";

import type { ConstraintCheck } from "../types";

const STATUS_CONFIG = {
  passed: {
    icon: "✓",
    containerClass: "bg-emerald-500/10 border-emerald-500/20",
    iconClass: "text-emerald-400",
    labelClass: "text-zinc-200",
  },
  failed: {
    icon: "✗",
    containerClass: "bg-red-500/10 border-red-500/20",
    iconClass: "text-red-400",
    labelClass: "text-zinc-200",
  },
  warning: {
    icon: "⚠",
    containerClass: "bg-yellow-500/10 border-yellow-500/20",
    iconClass: "text-yellow-400",
    labelClass: "text-zinc-200",
  },
};

interface Props {
  checks: ConstraintCheck[];
}

export default function ConstraintChecklist({ checks }: Props) {
  if (!checks.length) return null;

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4 space-y-3">
      <h2 className="text-sm font-semibold uppercase tracking-widest text-zinc-400">
        Constraint Verification
      </h2>

      <div className="space-y-2">
        {checks.map((check, i) => {
          const cfg = STATUS_CONFIG[check.status];
          return (
            <div
              key={i}
              className={`flex items-start gap-3 rounded-lg border px-3 py-2 ${cfg.containerClass}`}
            >
              <span className={`shrink-0 text-sm font-bold mt-0.5 ${cfg.iconClass}`}>
                {cfg.icon}
              </span>
              <div className="min-w-0">
                <p className={`text-sm font-medium ${cfg.labelClass}`}>
                  {check.constraint}
                </p>
                <p className="text-xs text-zinc-500 mt-0.5 leading-relaxed">
                  {check.detail}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
