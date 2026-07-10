import logging
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


async def get_exchange_rate(from_currency: str, to_currency: str) -> dict:
    """
    Fetch live exchange rate. Falls back to hardcoded approximate if key missing.
    Free tier: 1,500 requests/month.
    """
    if not settings.EXCHANGERATE_API_KEY:
        logger.warning("EXCHANGERATE_API_KEY not set — using fallback rates")
        return _fallback_rate(from_currency, to_currency)

    url = f"https://v6.exchangerate-api.com/v6/{settings.EXCHANGERATE_API_KEY}/pair/{from_currency}/{to_currency}"

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

            if data.get("result") == "success":
                return {
                    "from": from_currency,
                    "to": to_currency,
                    "rate": data["conversion_rate"],
                    "is_live": True,
                }
            return _fallback_rate(from_currency, to_currency)

        except Exception as e:
            logger.error("ExchangeRate error: %s", e)
            return _fallback_rate(from_currency, to_currency)


# Approximate fallback rates against INR
_FALLBACK_INR_RATES: dict[str, float] = {
    "JPY": 1.83, "USD": 0.012, "EUR": 0.011, "GBP": 0.0095,
    "THB": 0.43, "SGD": 0.016, "AED": 0.044,
}


def _fallback_rate(from_currency: str, to_currency: str) -> dict:
    rate = None
    if from_currency == "INR":
        rate = _FALLBACK_INR_RATES.get(to_currency)
    elif to_currency == "INR":
        base = _FALLBACK_INR_RATES.get(from_currency)
        rate = 1 / base if base else None

    return {
        "from": from_currency,
        "to": to_currency,
        "rate": rate or 1.0,
        "is_live": False,
        "note": "Approximate fallback rate — API key not configured or request failed.",
    }
