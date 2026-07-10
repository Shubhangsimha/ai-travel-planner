from pathlib import Path
from pydantic_settings import BaseSettings
from typing import List

# Resolve .env from backend/ or parent (project root) — whichever exists first.
_here = Path(__file__).parent  # backend/app/core/
_candidates = [
    _here / "../../../.env",   # project root when running from backend/
    _here / "../../.env",      # one level up
    Path(".env"),               # CWD fallback
]
_env_file = next((str(p.resolve()) for p in _candidates if p.exists()), ".env")


class Settings(BaseSettings):
    # LLM
    GEMINI_API_KEY: str = ""

    # Aviationstack (flight routes & schedules)
    AVIATIONSTACK_API_KEY: str = ""

    # Overpass API / OpenStreetMap (hotel POIs — no key required)
    OVERPASS_API_URL: str = "https://overpass-api.de/api/interpreter"

    # OpenTripMap
    OPENTRIPMAP_API_KEY: str = ""

    # ExchangeRate
    EXCHANGERATE_API_KEY: str = ""

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # App
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = _env_file
        env_file_encoding = "utf-8"


settings = Settings()
