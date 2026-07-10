"use client";

import { useAgentStream } from "./hooks/useAgentStream";
import GoalInputForm from "./components/GoalInputForm";
import AgentTracePanel from "./components/AgentTracePanel";
import ItineraryView from "./components/ItineraryView";
import BudgetBreakdownTable from "./components/BudgetBreakdownTable";
import ConstraintChecklist from "./components/ConstraintChecklist";
import DecisionExplanationPanel from "./components/DecisionExplanationPanel";
import DataDisclaimerBanner from "./components/DataDisclaimerBanner";

export default function Home() {
  const { traceEvents, result, error, isStreaming, startPlanning, reset } =
    useAgentStream();

  const hasActivity =
    isStreaming || traceEvents.length > 0 || result != null || error != null;

  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-100">
      {/* Header */}
      <header className="border-b border-zinc-800 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold tracking-tight">
              TripPilot <span className="text-indigo-400">AI</span>
            </h1>
            <p className="text-xs text-zinc-500">
              Agentic Travel Operations Platform
            </p>
          </div>
          {hasActivity && (
            <button
              onClick={reset}
              className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
            >
              ← New trip
            </button>
          )}
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Input + loading view */}
        {!result && (
          <div className="max-w-2xl mx-auto space-y-6">
            <div className="text-center space-y-2">
              <h2 className="text-2xl font-bold tracking-tight">
                Where do you want to go?
              </h2>
              <p className="text-sm text-zinc-500">
                Describe your trip in plain English. Our agents will research,
                plan, and optimize everything.
              </p>
            </div>

            <GoalInputForm onSubmit={startPlanning} isLoading={isStreaming} />

            {error && (
              <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3">
                <p className="text-sm text-red-400">{error}</p>
              </div>
            )}

            {traceEvents.length > 0 && (
              <div className="rounded-xl border border-zinc-800 bg-zinc-900 h-72 overflow-hidden">
                <AgentTracePanel
                  events={traceEvents}
                  isStreaming={isStreaming}
                />
              </div>
            )}
          </div>
        )}

        {/* Results layout */}
        {result && (
          <div className="space-y-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h2 className="text-xl font-bold">
                  {result.trip_goal?.destination} —{" "}
                  {result.trip_goal?.duration_days} Days
                </h2>
                <p className="text-sm text-zinc-500 mt-1">
                  {result.trip_goal?.start_date} to {result.trip_goal?.end_date}
                  {" · "}₹{result.trip_goal?.budget_inr?.toLocaleString("en-IN")} budget
                  {result.trip_goal?.interests?.length
                    ? ` · ${result.trip_goal.interests.join(", ")}`
                    : null}
                </p>
              </div>
            </div>

            <DataDisclaimerBanner result={result} />

            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
              {/* Left col — trace + itinerary + decisions */}
              <div className="xl:col-span-2 space-y-6">
                <div className="rounded-xl border border-zinc-800 bg-zinc-900 h-48 overflow-hidden">
                  <AgentTracePanel events={traceEvents} isStreaming={false} />
                </div>
                <ItineraryView days={result.itinerary_days} />
                <DecisionExplanationPanel
                  explanations={result.decision_explanations}
                />
              </div>

              {/* Right col — budget + constraints */}
              <div className="space-y-4">
                {result.budget_breakdown && (
                  <BudgetBreakdownTable budget={result.budget_breakdown} />
                )}
                <ConstraintChecklist checks={result.constraint_checks} />
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
