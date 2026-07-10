"""
Shared JSON parsing utility for all AI agent modules.
Handles Gemini's occasional non-compliant responses gracefully.
"""
import json
import re
import logging

logger = logging.getLogger(__name__)


def parse_llm_json(content: str, context: str = "") -> dict | list:
    """
    Parse JSON from an LLM response robustly.
    Tries in order:
      1. Direct parse after stripping markdown fences
      2. Extract first {...} or [...] block via regex
    Raises json.JSONDecodeError if both fail.
    """
    # Strip markdown fences
    cleaned = re.sub(r"^```(?:json)?\s*", "", content.strip())
    cleaned = re.sub(r"\s*```$", "", cleaned).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Try to extract the first JSON object or array
    match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", cleaned)
    if match:
        try:
            result = json.loads(match.group(1))
            logger.warning("JSON extracted via regex fallback%s", f" ({context})" if context else "")
            return result
        except json.JSONDecodeError:
            pass

    raise json.JSONDecodeError(
        f"Could not parse JSON from LLM response{f' ({context})' if context else ''}",
        cleaned, 0
    )
