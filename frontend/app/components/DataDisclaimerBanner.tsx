"use client";

import type { PlanResult } from "../types";

interface Props {
  result: PlanResult;
}

export default function DataDisclaimerBanner({ result }: Props) {
  const hasEstimated = Object.values(result.worker_results ?? {}).some(
    (w) => w.is_test_data
  );

  if (!hasEstimated) return null;

  return (
    <div className="flex items-start gap-3 rounded-lg border border-yellow-500/20 bg-yellow-500/5 px-4 py-3">
      <span className="shrink-0 text-yellow-400 text-sm mt-0.5">⚠</span>
      <p className="text-xs text-yellow-300/80 leading-relaxed">
        <span className="font-semibold">Flight and hotel prices are estimates.</span>{" "}
        Flight fares are computed from distance + seasonal data. Hotel rates are
        tier-based averages. Real-time pricing requires a paid booking API. All
        other data (weather, attractions, restaurants, exchange rates) is live.
      </p>
    </div>
  );
}
