import time
import httpx
import os

SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_SEARCH_URL = "https://api.spotify.com/v1/search"
EXPIRE_BUFFER = 60

# Cached token: spotify tokens last 1 hour
_token: str | None = None
_token_expires_at: float = 0

async def _get_token() -> str:
    global _token, _token_expires_at

    if _token and time.time() < _token_expires_at:
        return _token

    async with httpx.AsyncClient() as client:
        response = await client.post(
            SPOTIFY_TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=(os.environ["SPOTIFY_CLIENT_ID"], os.environ["SPOTIFY_CLIENT_SECRET"]),
        )
        response.raise_for_status()
        data = response.json()

    _token = data["access_token"]
    _token_expires_at = time.time() + data["expires_in"] - EXPIRE_BUFFER  # small buffer
    return _token

async def search_tracks(query: str, limit: int = 10) -> list[dict]:
    token = await _get_token()

    async with httpx.AsyncClient() as client:
        response = await client.get(
            SPOTIFY_SEARCH_URL,
            params={"q": query, "type": "track", "limit": limit},
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        items = response.json()["tracks"]["items"]

    # Only return tracks that have a 30s preview available
    return [
        {
            "track_id": t["id"],
            "track_name": t["name"],
            "artist_name": t["artists"][0]["name"],
            "album_art": t["album"]["images"][0]["url"] if t["album"]["images"] else None,
            "preview_url": t["preview_url"],
        }
        for t in items
        if t["preview_url"]
    ]
