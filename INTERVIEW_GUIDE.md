# TripPilot AI — Definitive Interview Preparation Guide

---

## Table of Contents

1. [Project Pitches](#1-project-pitches)
2. [Resume Summary](#2-resume-summary)
3. [Architecture Deep Dive](#3-architecture-deep-dive)
4. [End-to-End Flow](#4-end-to-end-flow)
5. [Every AI Component](#5-every-ai-component)
6. [Engineering Decisions](#6-engineering-decisions)
7. [Trade-offs](#7-trade-offs)
8. [Interview Questions](#8-interview-questions)
9. [Production Readiness](#9-production-readiness)
10. [Future Improvements](#10-future-improvements)
11. [Resume Formats](#11-resume-formats)
12. [HR Questions](#12-hr-questions)
13. [Mock Whiteboard](#13-mock-whiteboard)
14. [Final Review by Senior Engineers](#14-final-review-by-senior-engineers)

---

## 1. Project Pitches

### 30-Second Elevator Pitch

"I built TripPilot AI — an agentic travel planning platform where a team of specialised AI agents collaborates to generate a personalised day-by-day trip itinerary. You describe your trip in plain English and the system dispatches six research workers in parallel — weather, attractions, restaurants, hotels, flights, and currency — then a synthesis agent builds the plan, a critic agent reviews it in a loop until it meets all your constraints, and a decision explainer tells you exactly why every choice was made. The entire pipeline streams live to the frontend via Server-Sent Events."

---

### 60-Second Elevator Pitch

"TripPilot AI is a multi-agent travel planning system I designed and built from scratch. The core architecture is a three-tier hierarchy: an orchestrator graph, six parallel research workers, and a synthesis-critique loop. When a user describes their trip, a goal parser extracts structured intent — destination, dates, budget, interests, exclusions. Six workers then fire in parallel, each calling a different real API: Open-Meteo for weather, OpenTripMap for attractions and restaurants, Overpass API for hotels, Aviationstack for flight routes, and ExchangeRate-API for currency. A plan synthesizer then uses all that real data to generate a day-by-day itinerary, constraining the LLM to a computed per-day budget so it never hallucinates costs. A critic agent reviews the plan against the original goals and sends specific objections back for revision — up to three passes. A decision explainer then narrates the key choices made. The entire pipeline is orchestrated with LangGraph, served via FastAPI with async SSE streaming, and displayed in a Next.js dark-theme UI. Everything runs on free API tiers. The architecture demonstrates real production patterns: typed shared state, Python-enforced arithmetic, rate limiting, SSE timeouts, and Docker packaging."

---

### 2-Minute Explanation

"Let me walk you through TripPilot AI at a comfortable pace.

**The problem:** Travel planning is inherently a multi-source research problem. You need weather data, local attractions, restaurant options, hotel prices, flight costs, and currency conversion — and you need all of them before you can write a coherent plan. A single LLM call cannot do this reliably: it hallucinates prices, invents hotel names, and has no knowledge of current weather.

**The solution:** I decomposed the problem into a directed acyclic graph of specialised agents. The first node is a goal parser that extracts structured intent from free-form text — destination IATA code, budget in INR, duration, interests, exclusions, transport preference, whether the trip is domestic or international. The second node is a worker dispatcher that fires six research workers in parallel using asyncio.gather. Each worker calls a different real API and returns a structured result. Workers are stateless and disposable — if one fails, the plan continues with degraded data.

**The synthesis step:** Once all workers complete, a plan synthesizer receives a prompt that includes the real weather forecast, real attraction names, real restaurant names, real hotel options, and — critically — pre-computed fixed costs for flights and accommodation that the LLM is explicitly told it cannot change. The LLM's job is only to allocate the remaining budget across activities, food, and local transport. All budget arithmetic is then recomputed in Python and written back to the plan, so even if the LLM miscounts, the numbers are always correct.

**The critique loop:** A critic agent reviews the plan against the original constraints. If it rejects, it returns specific objections and the synthesizer revises. This runs up to three iterations. The critic is instructed to only evaluate controllable costs — activities and food — not the fixed flight or hotel costs, which prevents useless rejection loops on low-budget trips.

**The transparency layer:** A decision explainer generates plain-English narratives for the three key choices made: destination selection, accommodation choice, and main activity selection. A pure-Python constraint checker then verifies all constraints deterministically: budget, exclusions, transport preference, interests coverage, weather, and itinerary completeness.

**The frontend:** A Next.js app streams the planning trace live via SSE, then renders the full result: day-by-day itinerary with collapsible days, a budget breakdown table, a constraint checklist with pass/fail/warning badges, and the decision explanation panel. Everything is in a dark zinc-palette theme."

---

### 5-Minute Detailed Explanation

"I want to give you a thorough technical picture of TripPilot AI.

**Why I built it:** I wanted to demonstrate real agentic AI engineering — not a chatbot wrapper, not a single-prompt demo, but a production-quality system where multiple specialised agents coordinate through shared state, where failures are graceful, where all arithmetic is Python-enforced, and where the architecture decisions are deliberate and defensible.

**Architecture overview:** Three-tier hierarchy. Tier 1 is the LangGraph orchestrator — a StateGraph that defines the execution topology: parse → dispatch → synthesize → critique → explain → finalize. Tier 2 is six parallel research workers, each a pure async function calling one external API. Tier 3 is the synthesis-critique loop, which runs up to three iterations.

**LangGraph choice:** I chose LangGraph over raw chaining because it gives me a typed state machine with conditional edges. The critique loop — 'run critique, if rejected and iteration < 3 go back to synthesize, else continue' — is expressed as a conditional edge function. The entire graph is deterministic and inspectable. I can serialize the state at any node for debugging. LangGraph also lets me keep the orchestration logic separate from the agent implementations.

**Shared state:** PlannerState is a TypedDict with 14 fields. Every node reads from state and returns a partial dict — LangGraph merges it. This means no node needs to know about other nodes' internals. The critic node only needs trip_goal, itinerary_days, and budget_breakdown. The explainer node only needs trip_goal, itinerary_days, and budget_breakdown. Clean separation.

**Worker architecture:** Six workers: Weather (Open-Meteo free forecast API, with seasonal proxy tagging when trip dates exceed the 15-day window), Attractions (OpenTripMap, filtered by user interests), Restaurants (OpenTripMap, food category), Hotels (Overpass API for OSM hotel POIs, tier-priced by Python estimator), Flights (Aviationstack for route data, Python distance estimator for pricing — free tier only gives routes, not live fares), Currency (ExchangeRate-API). All six fire in asyncio.gather from a single dispatch node. All errors are caught and stored — a failing worker returns an empty result dict, never raises.

**The domestic trip problem:** A user asking for Goa from Delhi should get a domestic fare (₹7,000–10,000) not an international fare (₹24,000+). I solved this by building an INDIA_IATA_CODES set and computing is_domestic = origin_iata in set AND dest_iata in set. The flight estimator uses a lower per-km base rate and a table of 30 domestic Indian routes with real distances.

**Budget architecture — the hardest part:** The naive approach is to tell the LLM 'you have ₹1,20,000' and let it decide everything. The problem: it hallucinates hotel prices, miscomputes totals, and produces plans that grossly overrun. My approach: compute fixed costs in Python first — flight estimate from the flight worker, hotel estimate from the hotel worker (or 35% of budget as fallback). Subtract these from total budget to get available_for_activities. Pass this number explicitly to the synthesizer prompt. Recompute all daily totals from slot costs in Python after the LLM response. The LLM never does arithmetic — it only allocates slot-level costs within a clearly stated ceiling.

**The critique loop:** The critic sees fixed costs and controllable costs separately. It is explicitly instructed: reject only if controllable activity costs exceed the available budget, or if exclusions are violated, or if interests aren't reflected, or if transport preference is violated. It must not reject because the total budget including flights exceeds the stated budget — those costs are outside the planner's control. This prevents the useless rejection loop I hit in early testing where Goa trips were rejected three times because ₹31,000 flights exceeded a ₹20,000 budget.

**Streaming:** FastAPI runs the LangGraph synchronously in run_in_executor to avoid blocking the event loop. An asyncio.Queue per session accumulates events. A generator function yields SSE frames from the queue. The frontend EventSource connects before the planning starts, accumulates trace events live, then receives the final complete payload. A 5-minute timeout prevents zombie sessions.

**Frontend:** Next.js App Router with TypeScript, Tailwind v4, dark zinc theme. The AgentTracePanel shows every agent event live during planning. On completion: ItineraryView (collapsible day cards with morning/afternoon/evening slots), BudgetBreakdownTable (flight/hotel/activities/total/surplus), ConstraintChecklist (pass/fail/warning per constraint), DecisionExplanationPanel (plain English rationale for key choices), DataDisclaimerBanner (flags all estimated data). All nullable backend fields have correct TypeScript types.

**Rate limiting and reliability:** In-process rate limiter: max 5 concurrent planning jobs, max 10 requests per IP per hour. Input validation: 20–2000 characters. SSE timeout: 5 minutes. Critic loop cap: 3 iterations. Gemini errors produce human-readable messages via _clean_error() — no proto stack traces leak to the UI.

**Docker:** Separate Dockerfiles for backend (python:3.12-slim, non-root user) and frontend (node:20-alpine, 3-stage with Next.js standalone output). docker-compose with healthcheck and depends_on: service_healthy. NEXT_PUBLIC_API_URL set to localhost:8000 so the browser can reach the API."

---

## 2. Resume Summary

### One-Line Project Description

Built TripPilot AI — a production-quality multi-agent travel planning platform using LangGraph, Gemini 2.5 Flash, FastAPI, and Next.js where six parallel research workers feed a synthesis-critique loop that generates constraint-verified day-by-day itineraries with live SSE streaming.

---

### ATS-Friendly 2-Bullet Version

- **Built TripPilot AI**, a multi-agent travel planning system using **LangGraph**, **Gemini 2.5 Flash**, **FastAPI**, and **Next.js**; orchestrated 6 parallel async research workers (weather, attractions, hotels, flights, currency) feeding a synthesis-critique loop that iteratively refines itineraries against user constraints, with live **SSE streaming** and **Docker** deployment
- Implemented production-grade patterns including Python-enforced budget arithmetic (no LLM math), in-process rate limiting (5 concurrent / 10 req/IP/hr), 5-min SSE timeout, semantic exclusion matching, domestic vs. international flight detection across 50+ destinations, and typed **Pydantic v2** state management across a **LangGraph StateGraph**

---

### ATS-Friendly 4-Bullet Version

- **Built TripPilot AI**, a 3-tier multi-agent travel planning platform: LangGraph orchestrator → 6 parallel research workers → synthesis-critique loop; processes plain-English trip descriptions into verified day-by-day itineraries using real API data (Open-Meteo, OpenTripMap, Overpass, Aviationstack, ExchangeRate-API)
- Designed the **agentic pipeline** with Gemini 2.5 Flash: GoalParser extracts structured trip intent, PlanSynthesizer builds itineraries constrained to a Python-computed per-day budget, CritiqueOptimizer reviews and rejects on controllable costs only (up to 3 passes), DecisionExplainer generates plain-English rationale; all LLM JSON parsed with fallback regex extraction
- Implemented **production reliability** patterns: asyncio.gather for parallel worker execution, run_in_executor to keep FastAPI event loop non-blocking, asyncio.wait_for 5-min SSE timeout, in-process rate limiter (defaultdict of IP timestamps), 503/429 error codes, _clean_error() stripping gRPC proto boilerplate from user-facing messages
- Packaged with **Docker** (python:3.12-slim backend, node:20-alpine 3-stage frontend, docker-compose with healthcheck); frontend in **Next.js App Router** with TypeScript, Tailwind v4 dark theme, live AgentTracePanel, BudgetBreakdownTable, ConstraintChecklist, and DataDisclaimerBanner

---

### Recruiter-Friendly Project Description

**TripPilot AI — Agentic Travel Operations Platform**

TripPilot AI is a full-stack AI application that plans personalised travel itineraries using a team of specialised AI agents. Users describe their trip in plain English — destination, budget, dates, interests, what to avoid — and a multi-agent pipeline handles the rest.

Six research agents fire simultaneously to gather real data: weather forecasts, local attractions, restaurants, hotels, flight estimates, and currency rates. An AI planner then synthesises this data into a day-by-day itinerary. A critic agent reviews the plan and sends it back for revision if it violates any constraints. The whole process streams live to the screen so users can watch the agents work in real time.

**Tech stack:** Python, LangGraph, Gemini 2.5 Flash, FastAPI, Next.js, TypeScript, Tailwind CSS, Docker. All free APIs and free AI tier.

---

## 3. Architecture Deep Dive

### Overall Architecture

TripPilot AI uses a **3-tier hierarchical multi-agent architecture**:

```
Tier 1 — Orchestrator
  LangGraph StateGraph
  Defines execution topology and conditional edges
  Manages shared PlannerState TypedDict

Tier 2 — Research Workers (parallel)
  WeatherWorker       → Open-Meteo API
  AttractionsWorker   → OpenTripMap API
  RestaurantWorker    → OpenTripMap API
  HotelWorker         → Overpass API (OSM) + Python estimator
  FlightWorker        → Aviationstack API + Python estimator
  CurrencyWorker      → ExchangeRate-API

Tier 3 — Synthesis & Critique Loop
  PlanSynthesizer     → Gemini 2.5 Flash (itinerary generation)
  CritiqueOptimizer   → Gemini 2.5 Flash (plan review, max 3 passes)
  DecisionExplainer   → Gemini 2.5 Flash (rationale generation)
  ConstraintChecker   → Pure Python (deterministic verification)
```

The graph topology:

```
parse_goal → dispatch_workers → synthesize_plan → critique_plan
                                      ↑                  ↓
                                      └── (if rejected) ─┘
                                                         ↓
                                              (if approved or max iter)
                                                         ↓
                                           generate_explanations → finalize
```

The entire backend runs as a single FastAPI process. LangGraph runs synchronously in a thread pool executor. An asyncio.Queue per session bridges the sync graph to the async SSE stream.

---

### Why LangGraph

LangGraph solves the problem of **stateful agent orchestration** with conditional branching. The alternatives were:

- **Raw Python** — works, but the critique loop requires manual state passing, no standard way to add observability, harder to add nodes later
- **LangChain LCEL** — good for chains, not designed for loops or conditional branching
- **CrewAI / AutoGen** — higher-level, but less control over state, harder to enforce Python arithmetic over LLM results, opaque internals

LangGraph gives: typed StateGraph, conditional edges as plain Python functions, compile-time graph validation, and state serialisation. The critique loop is expressed as a single 5-line conditional edge function — clean, testable, inspectable.

---

### Why Multiple Agents

A single LLM call cannot reliably:
1. Know today's weather at a specific destination
2. Name real attractions at the destination
3. Return accurate hotel prices
4. Know current flight routes
5. Compute correct currency conversions
6. Do all of this simultaneously without context overflow

Multiple specialised agents solve this: each agent has a **narrow, well-defined contract**. The weather worker only does weather. It never sees restaurant data. This means each agent's prompt is smaller, its output is more predictable, and failures are isolated — if the hotel worker fails, the other five still complete.

---

### Why Not a Single LLM

A single LLM call for travel planning fails because:

1. **Hallucination:** LLMs invent hotel names, fabricate prices, and generate plausible-sounding but wrong attraction details
2. **Staleness:** Training cutoff means weather, exchange rates, and flight routes are unknown
3. **Arithmetic:** LLMs miscalculate multi-day budget totals — a known failure mode for all current models
4. **Context length:** Passing all real-world data (weather forecasts, attraction lists, hotel data) plus a multi-day itinerary in one prompt is expensive and degrades quality
5. **Accountability:** With a single call, you cannot tell which part of the response came from real data vs. hallucination

The multi-agent approach puts real data into every context window. The LLM's role is narrative — "given these real hotels, real attractions, and this exact budget ceiling, write the schedule." Arithmetic is Python.

---

### Worker Architecture

Each worker is a standalone `async def` function with this contract:

**Input:** `trip_goal: dict` (structured trip intent), `coords: dict` (lat/lon from geocoding, where needed)

**Output:** `(WorkerResult dict, TraceEvent dict)`

**Error contract:** All exceptions caught internally. Failed workers return `{success: False, data: {}, error: str}`. They never raise. The orchestrator continues with degraded data.

**Stateless:** Workers hold no state between calls. Each call is fully self-contained. This makes them independently testable and horizontally scalable.

Workers are dispatched via `asyncio.gather(*[w1, w2, w3, w4, w5, w6])` — true parallel I/O concurrency (not parallelism — Python GIL doesn't matter here because all workers are awaiting network I/O).

---

### Planner (GoalParser)

The GoalParser transforms free-form text into a validated `TripGoal` dict. It uses Gemini 2.5 Flash with a strict system prompt specifying an exact JSON schema. The LLM extracts: destination, origin city, duration, budget in INR, start/end dates, interests list, exclusions list, transport preference.

Post-processing (Python, not LLM): IATA code lookup, currency assignment, `is_domestic` flag computation, date consistency validation, `max(..., 1)` guards on budget and duration, end_date recomputation from start_date + duration.

---

### Synthesizer (PlanSynthesizer)

The Synthesizer receives: structured trip goal, all six worker results, and (on revision passes) a list of objections from the critic.

Pre-processing (Python): computes `fixed_total = flight_estimate + hotel_budget`, `available_budget = total_budget - fixed_total`, `per_day_budget = available_budget / duration_days`. These numbers are embedded in the prompt — the LLM is told the ceiling explicitly.

The prompt provides: real weather data, real attraction names, real restaurant names, real hotel options, fixed costs it cannot change, available budget it must stay within. The LLM only writes schedules and assigns slot-level costs.

Post-processing (Python): `compute_budget_breakdown` recomputes every `daily_total_inr` from the three slot costs. The LLM's own arithmetic is discarded. The surplus/deficit is computed in Python from the corrected totals.

---

### Critic (CritiqueOptimizer)

The Critic receives the itinerary summary, the budget breakdown, and the trip goal. It evaluates against seven criteria in the system prompt, but the user prompt contains a critical override: only reject on **controllable costs** (activities, food, local transport), not fixed costs (flights, accommodation).

The critic returns: `{approved: bool, objections: [str], score: 1-10}`. If rejected, objections are passed back to the synthesizer as `critique_context` — a bulleted list of specific issues. This gives the synthesizer actionable guidance, not a vague "try again."

The loop runs `while not approved and iteration < MAX_CRITIQUE_ITERATIONS (3)`. After three failures, the plan is approved as-is. The graph moves forward.

---

### Decision Explainer

The Decision Explainer generates three plain-English narratives: why this destination was chosen, why this accommodation was selected, and what the main activity theme is for the trip. It receives the final approved itinerary and trip goal.

This component serves a UX purpose: it makes the AI's decisions **legible** to the user. It transforms opaque model output into user-facing reasoning. In production AI systems, explainability is increasingly a regulatory and trust requirement.

---

### Shared State

`PlannerState` is a `TypedDict` with these fields:

```
session_id        str
raw_input         str
trip_goal         dict | None
worker_results    dict
itinerary_days    list[dict]
budget_breakdown  dict | None
critique_result   dict | None
critique_iteration int
constraint_checks list[dict]
decision_explanations list[dict]
trace_events      list[dict]
error             str | None
is_complete       bool
```

Every node returns a **partial dict** — only the fields it changes. LangGraph merges partial updates into the shared state. This means: no node needs to read fields it didn't write, no accidental overwrites of unrelated fields, and the state is always inspectable as a plain Python dict.

---

### SSE Streaming

Server-Sent Events (SSE) provides one-directional server-to-client streaming over HTTP. The flow:

1. Frontend POSTs to `/api/plan` → receives `session_id`
2. Frontend opens `EventSource` to `/api/stream/{session_id}`
3. `create_session` creates an `asyncio.Queue` keyed by `session_id`
4. `_run_planning` background task runs the LangGraph graph in a thread executor
5. After graph completes, all trace events are emitted to the queue
6. The SSE generator yields each event as `data: {json}\n\n`
7. A `None` sentinel closes the stream
8. `asyncio.wait_for(q.get(), timeout=300)` prevents zombie sessions

SSE was chosen over WebSockets because the communication is one-directional (server to client), SSE has automatic reconnection in browsers, and it is simpler to implement correctly with FastAPI's `StreamingResponse`.

---

### FastAPI

FastAPI provides: async request handling, Pydantic v2 request validation, automatic OpenAPI docs, and clean route organisation. The `run_in_executor` pattern allows the synchronous LangGraph graph to run in a thread pool without blocking the async event loop — a standard pattern for CPU/sync work in async Python services.

---

### Next.js

Next.js App Router provides: TypeScript by default, server-side rendering capabilities (though the app is fully client-side rendered in this project), Tailwind CSS v4 integration, and standalone output mode for Docker deployment. The three-stage Docker build (deps → builder → runner with standalone output) produces a minimal production image (~150MB).

---

### Docker

Two Dockerfiles:

**Backend:** `python:3.12-slim` base, non-root user (`appuser`), dependencies installed from `requirements.txt`, `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]`

**Frontend:** `node:20-alpine` three-stage: (1) deps — install node_modules, (2) builder — `npm run build` to generate `.next/standalone`, (3) runner — copy only the standalone output, minimal final image

**docker-compose:** Backend and frontend services, healthcheck on `/api/health`, `depends_on: condition: service_healthy`, `NEXT_PUBLIC_API_URL=http://localhost:8000` (browser-accessible, not Docker-internal)

---

### External APIs

| API | Purpose | Tier | Limit |
|-----|---------|------|-------|
| Gemini 2.5 Flash | LLM for all AI nodes | Free | 15 RPM, 1M tokens/day |
| Open-Meteo | Weather forecasts | Free, no key | Unlimited |
| OpenTripMap | Attractions, restaurants | Free | 5000 req/day |
| Nominatim (OSM) | Geocoding city → lat/lon | Free, no key | 1 req/sec |
| Overpass API | Hotel POIs from OSM | Free, no key | Rate-limited |
| Aviationstack | Flight route data | Free | 100 req/month |
| ExchangeRate-API | Currency rates | Free | 1500 req/month |

---

### Prompt Engineering Strategy

Four principles govern all prompts in TripPilot AI:

1. **Output format first:** Every system prompt specifies the exact JSON schema the LLM must return. No ambiguity about structure.

2. **Constraints before content:** Budget ceilings, exclusions, and transport preferences are listed before the request for creative content. Constraints frame the solution space.

3. **Real data, not instructions to research:** The LLM is never told to "find attractions in Tokyo." It is given a list of real attractions from the OpenTripMap worker. Its job is selection and scheduling, not research.

4. **Explicit arithmetic prohibition:** The synthesizer prompt says "All estimated_cost_inr values across all days must sum to no more than INR {available_budget}. Do NOT include flight or hotel costs in any slot." Python enforces this regardless — but the instruction reduces the frequency of violations and the number of critique iterations required.

**JSON robustness:** `parse_llm_json()` first strips markdown code fences then attempts direct `json.loads`. On failure, a regex fallback extracts the first `{...}` or `[...]` block. This handles the most common failure modes: LLMs that forget the no-fences instruction, or that add trailing explanation text after the JSON.

---

## 4. End-to-End Flow

### Step 1: User Prompt

User types into the GoalInputForm textarea: "I want to visit Goa for 5 days in December with ₹50,000. I love beaches and local food. Avoid nightlife. Mixed transport."

Frontend validates: trimmed length ≥ 20 chars. Submit button activates. On submit, `useAgentStream.startPlanning(input)` is called.

### Step 2: POST /api/plan

Frontend POSTs `{raw_input: "I want to visit..."}` to `/api/plan`. FastAPI validates the Pydantic `PlanRequest` (20–2000 chars). Rate limiter checks: are there fewer than 5 concurrent jobs? Has this IP made fewer than 10 requests in the last hour? If yes to both, a UUID `session_id` is generated, `create_session` creates the queue, `asyncio.create_task` launches `_run_planning` in the background, and the API returns `{session_id: "uuid"}` with HTTP 202.

### Step 3: SSE Connection

Frontend receives the `session_id` and immediately opens an `EventSource` connection to `/api/stream/{session_id}`. The `stream_events` generator waits up to 10 seconds for the queue to appear (handles the race condition where the client connects before `create_session` runs), then enters the `asyncio.wait_for` loop.

### Step 4: GoalParser Node

`_run_planning` emits an Orchestrator "started" trace event to the queue (immediately visible in frontend). Then calls `loop.run_in_executor(None, planner_graph.invoke, initial_state)` — the graph runs synchronously in a thread.

`parse_goal_node` calls `parse_goal(raw_input)`. Gemini 2.5 Flash receives the system prompt with the JSON schema and the user's text. It returns structured JSON: `{destination: "Goa", origin_city: "Delhi", duration_days: 5, budget_inr: 50000, start_date: "2026-12-01", interests: ["beach", "food"], exclusions: ["nightlife"], transport_preference: "mixed"}`.

Python post-processing: looks up "goa" in DESTINATION_IATA → "GOI", "delhi" → "DEL". Both in INDIA_IATA_CODES → `is_domestic=True`. Currency forced to "INR". end_date computed as start_date + 4 days = "2026-12-05". Budget validated: `max(50000, 1) = 50000`.

### Step 5: WorkerDispatcher Node

`dispatch_workers_node` calls `asyncio.run(run_all_workers(trip_goal))`. Inside, `city_to_coordinates("Goa")` calls Nominatim geocoding API → returns `{lat: 15.2993, lon: 74.124}`.

Six workers launch simultaneously via `asyncio.gather`:

- **WeatherWorker:** `start_date="2026-12-01"` is 145 days away. Open-Meteo only provides 15 days. Worker detects `beyond_window=True`, fetches current forecast as seasonal proxy, tags all forecasts with `seasonal_proxy=True`.
- **AttractionsWorker:** OpenTripMap query for lat/lon with radius 5000m, filtered by interests ["beach", "food"]. Returns Calangute Beach, Baga Beach, Candolim Beach, etc.
- **RestaurantWorker:** OpenTripMap food category query. Returns local restaurants.
- **CurrencyWorker:** ExchangeRate-API, INR to INR (domestic). Returns rate=1.0.
- **FlightWorker:** Aviationstack DEL→GOI route search. Python estimator: DEL-GOI = 1900km, domestic rate 4.5 INR/km, December multiplier 1.4 → 1900 × 4.5 × 1.4 = ₹11,970 per person.
- **HotelWorker:** Overpass API for hotels within 5km of Goa coords. Python tier estimator for mid-range hotel × 4 nights (duration - 1).

All six complete. Results keyed by worker name.

### Step 6: PlanSynthesizer Node

`synthesize_plan_node` (iteration 0):

Python pre-computation:
- `flight_estimate = 11,970`
- `hotel_budget = hotels[0].estimated_total_inr` (say 16,000 for 4 nights)
- `fixed_total = 27,970`
- `available_budget = 50,000 - 27,970 = 22,030`
- `per_day_budget = 22,030 / 5 = 4,406`

Prompt to Gemini includes: real weather note (seasonal proxy), real beach names, real restaurant names, real hotel names, explicit "REMAINING BUDGET FOR ACTIVITIES: INR 22,030 (approx INR 4,406/day)". LLM generates a 5-day JSON itinerary with morning/afternoon/evening slots, each with `estimated_cost_inr`.

Python post-computation: for every day, sum the three slot costs and write to `daily_total_inr`. Compute `activities_food_transport_inr = sum(daily_totals)`. Compute `total_inr = 11,970 + 16,000 + activities`. Compute `surplus_deficit_inr`.

### Step 7: CritiqueOptimizer Node

`critique_plan_node` (iteration 1):

Critic receives itinerary summary, budget breakdown, trip goal. Prompt shows: Flight INR 11,970, Hotel INR 16,000 (fixed, cannot change). Controllable: INR {activities_cost} of INR 22,030 available.

If activities cost ≤ 22,030 and no nightlife venues and beach/food are covered: approved, score 8/10. Graph moves forward.

If nightlife venue slipped in (e.g., "evening: beach bar"): rejected. Objections: ["Evening Day 3 includes a beach bar which violates the nightlife exclusion"]. Goes back to synthesizer with `critique_context`.

### Step 8: Synthesizer Revision (if needed)

Synthesizer receives objections: "Evening Day 3 includes a beach bar which violates the nightlife exclusion." It replaces that slot with a sunset walk and a local seafood dinner. New plan generated. Critic re-evaluates. If now approved, loop exits.

### Step 9: DecisionExplainer + ConstraintChecker

`generate_explanations_node`:
- `check_constraints` runs pure Python: Budget check, Exclusions scan (no nightlife keywords found), Transport check (mixed — no violations), Interests coverage (beach ✓, food ✓), Weather (warning: seasonal proxy — actual forecast unavailable), Itinerary completeness (5 of 5 days ✓).
- `generate_explanations` calls Gemini for three explanations: why Goa, why this hotel, what the trip theme is.

### Step 10: Finalize

`finalize_plan_node` emits the final trace event. Graph execution ends. `run_in_executor` returns the complete state dict.

### Step 11: SSE Complete Event

`_run_planning` iterates over `result["trace_events"]` and emits each to the queue. Then emits the `complete` event with: trip_goal, sanitized worker_results, itinerary_days, budget_breakdown, constraint_checks, decision_explanations.

### Step 12: Frontend Rendering

`useAgentStream` receives the `complete` event and sets `result` in React state. The loading view disappears. The results layout renders: trip header with destination/duration/budget, DataDisclaimerBanner, AgentTracePanel (now static, shows full trace), ItineraryView (5 collapsible day cards), BudgetBreakdownTable (flights/hotel/activities/total/surplus), ConstraintChecklist (6 checks with pass/warning/fail badges), DecisionExplanationPanel (3 explanation cards).

---

## 5. Every AI Component

### GoalParser

**Purpose:** Transform unstructured natural language trip description into a validated structured `TripGoal` dict that all downstream components can consume without parsing.

**Input:** `raw_input: str` — the user's free-form trip description

**Output:** `TripGoal dict` — destination, origin_city, destination_iata, origin_iata, duration_days, budget_inr, start_date, end_date, interests, exclusions, transport_preference, currency, is_domestic, raw_input

**Why it exists:** Downstream agents need structured data, not a string. The flight estimator needs IATA codes. The hotel worker needs a budget figure. The synthesizer needs a duration. Centralising this extraction into one LLM call with a validated schema means all downstream agents get clean data.

**Failure cases:**
- LLM returns malformed JSON → `parse_llm_json` regex fallback extracts first `{...}` block
- LLM omits a required field → Python fallbacks: default origin "Delhi", default duration 7, default budget 120000
- Destination not in IATA map → 3-char uppercase fallback (best effort)
- Date parsing fails → falls back to today + duration

**Alternatives:** Regex extraction (too brittle), Pydantic + function calling (more reliable but requires a more complex prompt setup), spaCy NER (no budget/date extraction).

**Trade-offs:** LLM extraction handles colloquial inputs ("next October", "about 1.5 lakh", "somewhere in Japan") that regex cannot. Cost: one Gemini call per planning request. Latency: ~1–2 seconds.

---

### PlanSynthesizer

**Purpose:** Generate a day-by-day itinerary that uses real worker data, respects a Python-computed budget ceiling, and incorporates specific objections from previous critique iterations.

**Input:** `trip_goal dict`, `worker_results dict`, `objections list[str] | None`

**Output:** `itinerary_days list[dict]` — each day has morning/afternoon/evening TimeSlot objects with activity, location, estimated_cost_inr, transport_to_next, notes

**Why it exists:** Itinerary generation requires creative narrative intelligence — understanding which attractions are near each other, how to pace a day, how to balance activity and food, how to adjust for arrival/departure days. This is the one task where LLM creative capability is genuinely needed. Everything else (costs, arithmetic, constraint checking) is handled in Python.

**Failure cases:**
- LLM returns list instead of object → `isinstance(data, list)` branch handles it
- LLM ignores budget ceiling → Python recomputes all daily_total_inr values regardless
- LLM puts hotel/flight costs in slots → critic will catch it; Python arithmetic corrects the breakdown
- Gemini quota exhausted → `_clean_error` returns human-readable message; node stores error in state

**Alternatives:** Template-based generation (no LLM creativity, rigid output), retrieval-augmented generation from a real itinerary database (better quality but requires database infrastructure).

**Trade-offs:** LLM creativity vs. cost. Each synthesis call uses ~2000–4000 tokens. On the free tier (15 RPM, 1M tokens/day), this is the most expensive node. Three revision passes can burn the daily free quota.

---

### CritiqueOptimizer

**Purpose:** Provide adversarial review of the synthesized plan and generate specific, actionable objections for the synthesizer to fix.

**Input:** `trip_goal dict`, `itinerary_days list[dict]`, `budget_breakdown dict`, `iteration int`

**Output:** `{approved: bool, objections: list[str], score: int, iteration: int}`

**Why it exists:** The synthesizer is generative — it produces a plausible plan. The critic is evaluative — it checks the plan against ground truth (the user's original constraints). Separating generation from evaluation is a core pattern in AI systems (like GANs, RLHF, Constitutional AI). The critic can catch: nightlife venues the synthesizer included when the user said "no nightlife," transport mode violations, budget overruns on controllable costs, days that don't reflect stated interests.

**Failure cases:**
- Critic rejects due to fixed costs (flights/hotel) → system prompt and user prompt both now explicitly instruct against this; the `available_budget` figure in the prompt makes the correct threshold clear
- Critic hallucinates violations that don't exist → score may still be high; `approved=false` with non-existent objections causes a useless revision pass but eventually the cap (3 iterations) exits the loop
- Gemini quota error → exception caught in `critique_plan_node`, auto-approve with empty objections, planning continues

**Alternatives:** Rule-based critic (deterministic but rigid, misses semantic violations like "the user said beach but there are no beach activities"), embedding-similarity check (doesn't understand complex constraint combinations).

**Trade-offs:** LLM critic can catch semantic violations (e.g., "the evening activity at a sake bar violates the alcohol exclusion") that a keyword checker would miss. Cost: one Gemini call per iteration. Up to 3 iterations = up to 3 additional calls.

---

### DecisionExplainer

**Purpose:** Generate plain-English narratives explaining the key decisions made in the plan so the user understands why the AI chose what it chose.

**Input:** `trip_goal dict`, `itinerary_days list[dict]`, `budget_breakdown dict`

**Output:** `list[dict]` — each item has `decision: str`, `explanation: str`, `confidence: str`

**Why it exists:** Explainability is a core requirement for trust in AI-generated plans. A user who sees "Day 3 morning: Calangute Beach" without context doesn't know if this is a real beach, why it was chosen over other beaches, or why it's in the morning. The explainer fills this gap. It also demonstrates production-quality AI engineering — real systems need to be auditable, not just functional.

**Failure cases:**
- Explanation generation fails → exception caught in `generate_explanations_node`, `explanations=[]`, planning continues
- LLM generates vague/generic explanations → no automatic retry; the explanation panel is a UX enhancement, not a blocker

**Alternatives:** Template-based explanations (e.g., "We chose {hotel} because it was the highest-rated option within your budget") — deterministic and reliable, but less natural.

---

### ConstraintChecker

**Purpose:** Deterministically verify that the final plan satisfies all user constraints.

**Input:** `trip_goal dict`, `itinerary_days list[dict]`, `budget_breakdown dict`, `worker_results dict`

**Output:** `list[dict]` — each item has `constraint: str`, `status: "passed"|"failed"|"warning"`, `detail: str`

**Why it exists:** The critic is probabilistic — it may miss a violation or hallucinate one. The constraint checker is deterministic Python code. It gives users a verifiable, reliable checklist. It also provides the `status` values that drive the UI badges (green/red/yellow).

**Why pure Python:** Constraint checking must not hallucinate. "Did the plan include a museum when the user said no museums?" is a string matching problem, not a reasoning problem. The `EXCLUSION_KEYWORD_MAP` provides semantic expansion (so "no museums" also catches "gallery", "exhibition") without involving an LLM.

**Failure cases:**
- Semantic gaps in EXCLUSION_KEYWORD_MAP → covered terms miss niche exclusions (e.g., "no water sports" would not match "kayaking")
- Interests matching is substring-based → "cafe" would not match "patisserie" (false negative)
- These are known limitations documented in the data disclaimer

---

## 6. Engineering Decisions

### Why LangGraph

LangGraph was chosen because the critique loop requires **conditional branching with state persistence**. After critique, the graph must either loop back to the synthesizer (with updated objections in state) or proceed to the explainer. This is not a linear chain — it's a graph with a cycle. LangGraph's `StateGraph` + conditional edges is the cleanest way to express this in Python. It also provides compile-time graph validation, state typing, and a clear separation between graph topology (in `graph.py`) and node logic (in `nodes.py`).

### Why FastAPI

FastAPI was chosen for: native async support (critical for non-blocking SSE streaming), Pydantic v2 validation (request body validation, type-safe models), and automatic OpenAPI docs. The `run_in_executor` pattern for sync LangGraph in an async service is idiomatic FastAPI. Flask would work but lacks native async. Django is too heavyweight for a single-endpoint AI service.

### Why Next.js

Next.js was chosen for: TypeScript by default, App Router file-based routing, Tailwind CSS v4 integration, and the `output: 'standalone'` mode that generates a minimal Docker-deployable image. The project doesn't need SSR — all data comes from the SSE stream — but Next.js provides a production-quality React setup without manual webpack configuration.

### Why Gemini 2.5 Flash

Gemini 2.5 Flash was chosen because: (1) the free tier (15 RPM, 1M tokens/day) is sufficient for the demo, (2) it handles structured JSON output reliably, (3) it has a large context window (1M tokens) which matters for the synthesizer prompt that includes multiple worker data summaries, and (4) it integrates cleanly with LangChain via `langchain-google-genai`. GPT-4o would be more capable but requires paid API access.

### Why OpenStreetMap (Nominatim + Overpass + OpenTripMap)

OpenStreetMap provides three free services that cover three different needs: Nominatim for geocoding (city name → coordinates), Overpass for POI queries (hotel locations), and OpenTripMap for categorised attractions and restaurants. All are free with no API key required for moderate use. The tradeoff is rate limits and less structured data than commercial alternatives.

### Why Aviationstack

Aviationstack's free tier provides flight route data (which airlines fly which routes) without live pricing. This is used to show which airlines serve the route — a signal of feasibility — while Python does the price estimation from distance and seasonality. The free tier is 100 requests/month, which is enough for portfolio demos.

### Why Open-Meteo

Open-Meteo provides a completely free, no-API-key weather forecast API with 15-day hourly and daily data. It is more reliable and more generous than any other free weather API. The seasonal proxy feature (fetching current-date forecasts as a proxy when trip dates exceed 15 days) gracefully handles the most common case in travel planning (trips planned weeks in advance).

### Why SSE (Server-Sent Events)

SSE was chosen over WebSockets because the communication is **one-directional**: the server streams events to the client, and the client never needs to send messages mid-stream. SSE is simpler to implement (a generator function + `StreamingResponse` in FastAPI), has automatic browser reconnection, works through HTTP/1.1 proxies and CDNs, and doesn't require a separate WebSocket upgrade handshake. WebSockets would be needed only if the frontend needed to send messages during planning (e.g., to pause or redirect the agents mid-run).

### Why Pydantic

Pydantic v2 is used for: request body validation (`PlanRequest`), ensuring `raw_input` is between 20 and 2000 characters before any expensive LLM call is made, and type-safe model definitions throughout the backend. Pydantic v2's `field_validator` with `mode='before'` allows the strip-and-validate pattern cleanly.

### Why Asyncio

The six research workers are all I/O-bound — each is awaiting a network response. Python's asyncio allows all six to be in flight simultaneously on a single thread. `asyncio.gather` launches all six coroutines and awaits all completions. This reduces the worker phase from ~18 seconds (sequential) to ~3–5 seconds (parallel), a 4-6x speedup. `asyncio.wait_for` provides timeout semantics for the SSE queue without polling.

---

## 7. Trade-offs

### Why Not CrewAI

CrewAI provides a higher-level abstraction where agents have roles, goals, and backstories, and a crew object manages execution. The tradeoff:
- **Pro:** Less boilerplate for role-based agent definitions
- **Con:** Less control over state — CrewAI manages state internally, making it harder to enforce Python arithmetic over LLM results, harder to add custom conditional branching (the critique loop), and harder to inspect intermediate state for debugging
- **Con:** CrewAI's parallel execution model is less explicit — harder to control and observe than `asyncio.gather`
- **Con:** Less transparency — the framework does more, which means you understand less and can explain less in interviews

For a portfolio project where **explaining every decision** is the goal, LangGraph's explicitness is an advantage.

### Why Not AutoGen

AutoGen is designed for **conversational multi-agent systems** where agents exchange messages in a dialogue. Travel planning is not conversational between agents — it is a **data pipeline** where each stage transforms a structured artifact. AutoGen would add conversational overhead (agents negotiating with each other) where we need deterministic orchestration (this node, then this node, then conditionally loop).

### Why Not OpenAI Agents SDK

The OpenAI Agents SDK (formerly Swarm) is tightly coupled to OpenAI models and tools. Using it would mean: no Gemini, no free tier, paid API required for every demo, vendor lock-in. The SDK is well-designed but this project deliberately uses free APIs across the stack.

### Why Not Temporal

Temporal is a workflow orchestration engine designed for durable, long-running, retryable workflows. It provides: activity retries with exponential backoff, workflow versioning, and persistence across process restarts. For a portfolio project that runs in a single process and completes within minutes, Temporal's operational complexity (separate server, SDK, namespace management) is not justified. LangGraph provides sufficient orchestration within a single process. Temporal would be the right choice at scale: planning workflows that take hours, require human approval steps, or must survive server restarts.

### Why Not Kafka

Kafka is a distributed event streaming platform designed for high-throughput, persistent, replayable event streams. For a single-instance portfolio app, it would add: broker setup, topic management, consumer group configuration, and message serialization complexity — all for a use case (one SSE stream per planning session) that asyncio.Queue handles in 20 lines of code. Kafka becomes relevant when multiple backend instances need to share session state, or when event replay and auditing are required at scale.

### Why Not WebSockets

WebSockets provide bidirectional communication. The SSE use case here is strictly one-directional: the server pushes events, the client only receives. WebSockets would require: an upgrade handshake, connection management, ping/pong heartbeats, and more complex client-side handling. SSE is simpler, more appropriate for the use case, and works correctly through HTTP/2 and most proxies. The only scenario where WebSockets would be needed is if users could send instructions mid-planning (pause, redirect, provide clarification) — a feature deliberately excluded from this version.

### Why Not REST Polling

REST polling (client repeatedly calls GET /status/{session_id}) has higher latency (depends on polling interval), higher server load (many repeated requests), and more complex client logic (polling loop, backoff, deduplication). SSE provides true push semantics with no polling overhead. The polling approach would be appropriate for very long-running background jobs (minutes to hours) where the client doesn't need near-realtime updates, but for a 30–60 second planning pipeline, SSE is clearly superior.

### Why Not Google Maps

Google Maps Platform (Places API, Directions API) requires a billing account and charges per request after the $200/month free credit. For a portfolio project, this is a real cost risk if demos go viral or during stress testing. OpenStreetMap + OpenTripMap + Nominatim provide equivalent functionality — geocoding, POI search, restaurant data — for free with no billing account required. The data quality is slightly lower than Google Maps for niche locations, but sufficient for all demo destinations.

### Why Not Amadeus

Amadeus is the standard API for real flight availability and pricing. The self-service tier requires registration, credential management, and has usage limits. More importantly, live flight availability requires payment information for booking — providing live prices without booking capability creates a confusing UX. The Python distance-based estimator approach is more honest: it says "estimated price" explicitly, never pretends to offer booking, and works for any route without API quota concerns.

---
