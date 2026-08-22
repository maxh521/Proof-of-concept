"""
Tiny URL Shortener API
-----------------------
A minimal but complete example of a REST API built with FastAPI.

Features:
- POST /shorten   -> create a short code for a long URL
- GET  /{code}    -> redirect to the original URL (and track clicks)
- GET  /stats/{code} -> view click count + metadata

Run locally:
    pip install -r requirements.txt
    uvicorn main:app --reload

Then visit http://127.0.0.1:8000/docs for interactive API docs.
"""

from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl

app = FastAPI(
    title="Tiny URL Shortener",
    description="A minimal URL shortening service.",
    version="1.0.0",
)

# In-memory "database". A real service would use Redis/Postgres/etc.
# Structure: { code: {"url": str, "created_at": datetime, "clicks": int} }
_store: dict[str, dict] = {}

_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
_counter = 0  # monotonically increasing id used to derive short codes


def _encode(n: int) -> str:
    """Encode a non-negative integer into a base62 string."""
    if n == 0:
        return _ALPHABET[0]
    digits = []
    base = len(_ALPHABET)
    while n:
        n, rem = divmod(n, base)
        digits.append(_ALPHABET[rem])
    return "".join(reversed(digits))


class ShortenRequest(BaseModel):
    url: HttpUrl


class ShortenResponse(BaseModel):
    code: str
    short_url: str
    original_url: str


class StatsResponse(BaseModel):
    code: str
    original_url: str
    created_at: datetime
    clicks: int


@app.post("/shorten", response_model=ShortenResponse, status_code=201)
def shorten_url(payload: ShortenRequest) -> ShortenResponse:
    """Create a short code for the given URL."""
    global _counter

    # Reuse an existing code if this URL was already shortened.
    for code, entry in _store.items():
        if entry["url"] == str(payload.url):
            return ShortenResponse(
                code=code, short_url=f"/{code}", original_url=entry["url"]
            )

    code = _encode(_counter)
    _counter += 1

    _store[code] = {
        "url": str(payload.url),
        "created_at": datetime.now(timezone.utc),
        "clicks": 0,
    }

    return ShortenResponse(code=code, short_url=f"/{code}", original_url=str(payload.url))


@app.get("/stats/{code}", response_model=StatsResponse)
def get_stats(code: str) -> StatsResponse:
    """Return metadata and click count for a short code."""
    entry = _store.get(code)
    if entry is None:
        raise HTTPException(status_code=404, detail="Short code not found")

    return StatsResponse(
        code=code,
        original_url=entry["url"],
        created_at=entry["created_at"],
        clicks=entry["clicks"],
    )


@app.get("/{code}")
def redirect_to_url(code: str):
    """Redirect to the original URL and increment the click counter."""
    entry = _store.get(code)
    if entry is None:
        raise HTTPException(status_code=404, detail="Short code not found")

    entry["clicks"] += 1
    return RedirectResponse(url=entry["url"])
