"""
google_books.py — Google Books API client for BookRecommendationApp.

Securely reads the API key from Streamlit secrets (or environment variable
as fallback). All network errors are caught and returned as empty dicts so
the application never crashes due to API unavailability.
"""

import requests
import streamlit as st

# ---------------------------------------------------------------------------
# API key resolution — order of precedence:
#   1. st.secrets["GOOGLE_BOOKS_API_KEY"]   (preferred — local secrets.toml)
#   2. os.environ["GOOGLE_BOOKS_API_KEY"]   (CI / deployment env var)
#   3. None → API calls are skipped gracefully
# ---------------------------------------------------------------------------

import os

def _get_api_key() -> str | None:
    """Return the Google Books API key without exposing it in logs or UI."""
    try:
        return st.secrets["GOOGLE_BOOKS_API_KEY"]
    except (KeyError, FileNotFoundError, AttributeError):
        pass
    return os.environ.get("GOOGLE_BOOKS_API_KEY")


# Base URL template
_BASE_URL = (
    "https://www.googleapis.com/books/v1/volumes"
    "?q={query}&orderBy=newest&maxResults=10&key={key}"
)

_TIMEOUT_SECONDS = 5


def get_new_books(query: str = "fiction") -> dict:
    """
    Search Google Books API for *query* and return the raw response dict.

    Returns an empty dict ``{}`` on any error condition (network failure,
    timeout, quota exceeded, malformed JSON, missing API key) so callers
    can safely check ``"items" in result`` without try/except.

    Parameters
    ----------
    query : str
        The search term to send to the Google Books API.

    Returns
    -------
    dict
        Parsed JSON response from the API, or ``{}`` on failure.
    """
    api_key = _get_api_key()

    if not api_key:
        # No key available — return empty dict; UI will degrade gracefully
        return {"_error": "no_api_key"}

    # Sanitise query: strip leading/trailing whitespace
    query = str(query).strip()
    if not query:
        return {}

    url = _BASE_URL.format(query=requests.utils.quote(query), key=api_key)

    try:
        response = requests.get(url, timeout=_TIMEOUT_SECONDS)
        response.raise_for_status()          # raises HTTPError for 4xx / 5xx
        data = response.json()
        return data if isinstance(data, dict) else {}

    except requests.exceptions.ConnectionError:
        return {"_error": "connection_error"}
    except requests.exceptions.Timeout:
        return {"_error": "timeout"}
    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else 0
        if status == 429:
            return {"_error": "rate_limited"}
        return {"_error": f"http_{status}"}
    except (ValueError, KeyError):
        # JSON decode failure or unexpected structure
        return {"_error": "bad_response"}
    except Exception:
        # Catch-all — never let a Books API failure crash the app
        return {"_error": "unknown"}


def get_error_message(data: dict) -> str | None:
    """
    Return a human-friendly error message if *data* contains an ``_error``
    key, otherwise return ``None`` (no error).
    """
    error_map = {
        "no_api_key":      "Google Books API key not configured.",
        "connection_error": "Could not connect to Google Books.",
        "timeout":         "Google Books request timed out.",
        "rate_limited":    "Google Books rate limit reached. Try again shortly.",
        "bad_response":    "Received an unexpected response from Google Books.",
        "unknown":         "Google Books is temporarily unavailable.",
    }
    err = data.get("_error")
    if err is None:
        return None
    # Handle http_4xx style errors
    if err.startswith("http_"):
        return f"Google Books returned an error (HTTP {err[5:]})."
    return error_map.get(err, "Google Books is temporarily unavailable.")


if __name__ == "__main__":
    # Quick smoke-test (requires GOOGLE_BOOKS_API_KEY env var)
    result = get_new_books("The Hobbit")
    if "items" in result:
        print(f"Found {len(result['items'])} results.")
        print("First title:", result["items"][0]["volumeInfo"].get("title"))
    elif "_error" in result:
        print("Error:", get_error_message(result))
    else:
        print("No results.")