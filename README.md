# TripPilot AI — Agentic Travel Operations Platform

A multi-agent travel planner built with LangGraph + Gemini 2.5 Flash, FastAPI, and Next.js.

**Architecture:** 3-tier hierarchical agents — Orchestrator → 6 parallel Research Workers → Synthesizer + Critique loop (max 3 iterations) → Decision Explainer.

---

## Quick Start (Docker)

### 1. Get API keys (all free tiers)

| Service | Purpose | Where to register |
|---|---|---|
| Google Gemini | LLM for all AI nodes | https://aistudio.google.com/app/apikey |
| Aviationstack | Real flight routes/schedules | https://aviationstack.com (100 req/month free) |
| OpenTripMap | Attractions & restaurants | https://opentripmap.io/product |
| ExchangeRate-API | Live currency rates | https://www.exchangerate-api.com (1,500 req/month free) |

Open-Meteo and Overpass/OSM are used for weather and hotels — **no keys required**.

### 2. Create `.env`

```bash
cp .env.example .env
# Fill in your keys
```

### 3. Start everything

```bash
docker compose up --build
```

- **Frontend:** http://localhost:3000
- **API:** http://localhost:8000
- **API docs:** http://localhost:8000/docs

---

## Local Development (no Docker)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend reads `NEXT_PUBLIC_API_URL` from `frontend/.env.local`. Default: `http://localhost:8000`.

---

## How It Works

1. **Goal Parser** — Gemini extracts destination, budget, dates, interests, exclusions from free-form text.
2. **6 Research Workers** run in parallel:
   - WeatherWorker — Open-Meteo (live forecast/archive)
   - AttractionsWorker — OpenTripMap
   - RestaurantWorker — OpenTripMap
   - CurrencyWorker — ExchangeRate-API
   - FlightWorker — Aviationstack routes + Python price estimator
   - HotelWorker — Overpass/OSM POIs + tier-based price estimator
3. **Synthesizer** — Gemini builds a day-by-day itinerary using all worker data.
4. **Critic** — Gemini reviews the plan against the original goal; flags violations and triggers replanning (up to 3 iterations).
5. **Explainer** — Gemini narrates the 5 most important decisions.
6. **Constraint Checker** — Pure Python verifies budget, exclusions, transport preference, weather.

All results stream to the browser via Server-Sent Events as they are produced.

---

## Known Limitations

- **Flight prices are estimates** — computed from distance + seasonal multipliers, not live fares. Aviationstack free tier provides routes and schedules only.
- **Hotel prices are estimates** — tier-based averages (budget/mid/luxury) per city, not live rates.
- **Aviationstack free tier** has 100 requests/month. The app checks availability without consuming quota on every keypress.
- **Open-Meteo forecast window** is 16 days. Dates beyond that window are clamped to today+15; past dates use the archive API.
- **Gemini rate limits** — if the free Gemini tier is exhausted, the API returns an error message in the stream.
- All data except flights and hotels is live from real APIs.
