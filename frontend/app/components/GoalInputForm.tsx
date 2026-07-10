"use client";

import { useState } from "react";

const EXAMPLE = `I have ₹1,20,000. I want to visit Japan for 8 days in October.
I love anime, cafés, photography and local food.
Avoid museums. I prefer public transport.`;

interface Props {
  onSubmit: (input: string) => void;
  isLoading: boolean;
}

export default function GoalInputForm({ onSubmit, isLoading }: Props) {
  const [value, setValue] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = value.trim();
    if (trimmed) onSubmit(trimmed);
  }

  function handleExample() {
    setValue(EXAMPLE);
  }

  const charCount = value.length;
  const canSubmit = value.trim().length > 10 && !isLoading;

  return (
    <form onSubmit={handleSubmit} className="w-full space-y-3">
      <div className="relative">
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          disabled={isLoading}
          placeholder="Describe your trip — budget, destination, dates, interests, anything you want to avoid..."
          rows={5}
          className="w-full resize-none rounded-xl border border-zinc-700 bg-zinc-900 px-4 py-3 text-sm text-zinc-100 placeholder-zinc-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:opacity-50"
        />
        <span className="absolute bottom-3 right-3 text-xs text-zinc-600">
          {charCount}
        </span>
      </div>

      <div className="flex items-center justify-between gap-3">
        <button
          type="button"
          onClick={handleExample}
          disabled={isLoading}
          className="text-xs text-indigo-400 hover:text-indigo-300 disabled:opacity-40 underline underline-offset-2"
        >
          Use example
        </button>

        <button
          type="submit"
          disabled={!canSubmit}
          className="rounded-lg bg-indigo-600 px-5 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-40 transition-colors"
        >
          {isLoading ? "Planning…" : "Plan my trip →"}
        </button>
      </div>
    </form>
  );
}
