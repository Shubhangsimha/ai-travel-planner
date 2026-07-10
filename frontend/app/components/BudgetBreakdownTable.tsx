"use client";

import type { BudgetBreakdown } from "../types";

interface Props {
  budget: BudgetBreakdown;
}

function Row({
  label,
  amount,
  muted,
}: {
  label: string;
  amount: number;
  muted?: boolean;
}) {
  return (
    <div
      className={`flex items-center justify-between py-2 border-b border-zinc-800 last:border-0 ${muted ? "text-zinc-500" : "text-zinc-200"}`}
    >
      <span className="text-sm">{label}</span>
      <span className="text-sm tabular-nums">
        ₹{amount?.toLocaleString("en-IN") ?? 0}
      </span>
    </div>
  );
}

export default function BudgetBreakdownTable({ budget }: Props) {
  const surplus = budget.surplus_deficit_inr ?? 0;
  const used = budget.total_inr ?? 0;
  const limit = budget.budget_limit_inr ?? 1;
  const pct = Math.min(100, Math.round((used / limit) * 100));

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4 space-y-3">
      <h2 className="text-sm font-semibold uppercase tracking-widest text-zinc-400">
        Budget Breakdown
      </h2>

      {/* Progress bar */}
      <div className="space-y-1">
        <div className="h-2 rounded-full bg-zinc-800 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${surplus >= 0 ? "bg-emerald-500" : "bg-red-500"}`}
            style={{ width: `${pct}%` }}
          />
        </div>
        <div className="flex justify-between text-[10px] text-zinc-600">
          <span>₹0</span>
          <span>₹{limit.toLocaleString("en-IN")}</span>
        </div>
      </div>

      <div className="divide-y divide-zinc-800">
        <Row label="Flights (estimated)" amount={budget.flights_inr} />
        <Row label="Accommodation (estimated)" amount={budget.accommodation_inr} />
        <Row
          label="Activities + Food + Transport"
          amount={budget.activities_food_transport_inr}
        />
      </div>

      {/* Total row */}
      <div className="flex items-center justify-between pt-2 border-t border-zinc-700">
        <span className="text-sm font-semibold text-zinc-200">Total</span>
        <span className="text-sm font-semibold tabular-nums text-zinc-200">
          ₹{used.toLocaleString("en-IN")}
        </span>
      </div>

      {/* Surplus / Deficit */}
      <div
        className={`flex items-center justify-between rounded-lg px-3 py-2 ${
          surplus >= 0
            ? "bg-emerald-500/10 border border-emerald-500/20"
            : "bg-red-500/10 border border-red-500/20"
        }`}
      >
        <span
          className={`text-sm font-medium ${surplus >= 0 ? "text-emerald-400" : "text-red-400"}`}
        >
          {surplus >= 0 ? "Under budget" : "Over budget"}
        </span>
        <span
          className={`text-sm font-bold tabular-nums ${surplus >= 0 ? "text-emerald-400" : "text-red-400"}`}
        >
          {surplus >= 0 ? "+" : ""}₹{surplus.toLocaleString("en-IN")}
        </span>
      </div>
    </div>
  );
}
