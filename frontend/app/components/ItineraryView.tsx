"use client";

import type { ItineraryDay, TimeSlot } from "../types";

function SlotCard({ slot, label }: { slot: TimeSlot | null | undefined; label: string }) {
  if (!slot) return null;
  return (
    <div className="flex gap-3">
      <div className="w-20 shrink-0 text-right">
        <span className="text-[10px] uppercase tracking-widest text-zinc-500 font-semibold">
          {label}
        </span>
        <div className="text-xs text-zinc-600 mt-0.5">{slot.time}</div>
      </div>
      <div className="flex-1 border-l border-zinc-800 pl-3 pb-4">
        <p className="text-sm font-medium text-zinc-100 leading-snug">
          {slot.activity}
        </p>
        <p className="text-xs text-indigo-400 mt-0.5">{slot.location}</p>
        <div className="flex flex-wrap items-center gap-2 mt-1">
          <span className="text-xs text-zinc-500">
            INR {slot.estimated_cost_inr?.toLocaleString("en-IN") ?? 0}
          </span>
          {slot.transport_to_next && (
            <span className="text-xs text-zinc-600">
              → {slot.transport_to_next}
            </span>
          )}
        </div>
        {slot.notes && (
          <p className="text-xs text-zinc-600 mt-1 italic">{slot.notes}</p>
        )}
      </div>
    </div>
  );
}

interface Props {
  days: ItineraryDay[];
}

export default function ItineraryView({ days }: Props) {
  if (!days.length) return null;

  return (
    <div className="space-y-4">
      <h2 className="text-sm font-semibold uppercase tracking-widest text-zinc-400">
        Day-by-Day Itinerary
      </h2>

      <div className="space-y-3">
        {days.map((day) => (
          <details
            key={day.day_number}
            className="group rounded-xl border border-zinc-800 bg-zinc-900 overflow-hidden"
            open={day.day_number === 1}
          >
            <summary className="flex cursor-pointer items-center justify-between px-4 py-3 select-none hover:bg-zinc-800/50 transition-colors">
              <div className="flex items-center gap-3">
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-indigo-600/20 text-xs font-bold text-indigo-400">
                  {day.day_number}
                </span>
                <div>
                  <span className="text-sm font-medium text-zinc-100">
                    {new Date(day.date + "T00:00:00").toLocaleDateString("en-IN", {
                      weekday: "short",
                      month: "short",
                      day: "numeric",
                    })}
                  </span>
                  {day.weather_summary && (
                    <span className="ml-2 text-xs text-zinc-500">
                      {day.weather_summary}
                    </span>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs text-zinc-500">
                  INR {day.daily_total_inr?.toLocaleString("en-IN") ?? 0}
                </span>
                <span className="text-zinc-600 group-open:rotate-90 transition-transform text-xs">
                  ▶
                </span>
              </div>
            </summary>

            <div className="px-4 py-3 border-t border-zinc-800 space-y-0">
              <SlotCard slot={day.morning} label="Morning" />
              <SlotCard slot={day.afternoon} label="Afternoon" />
              <SlotCard slot={day.evening} label="Evening" />
            </div>
          </details>
        ))}
      </div>
    </div>
  );
}
