# routes/dictionary.py
from fastapi import APIRouter, HTTPException
import httpx

router = APIRouter(prefix="/dictionary", tags=["dictionary"])

# freedictionaryapi.com uses a different base URL and no /en/ in the path
FREE_DICTIONARY_API = "https://freedictionaryapi.com/api/v1/entries"

@router.get("/{word}")
async def lookup_word(word: str):
    """Proxy for freedictionaryapi.com — avoids CORS issues in the browser."""
    async with httpx.AsyncClient(timeout=12) as client:
        for attempt in range(2):  # Retry once on timeout
            try:
                r = await client.get(f"{FREE_DICTIONARY_API}/{word}")
                if r.status_code == 404:
                    raise HTTPException(status_code=404, detail="Word not found")
                r.raise_for_status()
                return r.json()
            except httpx.TimeoutException:
                if attempt == 1:
                    raise HTTPException(status_code=504, detail="Dictionary timed out")
                continue
            except httpx.HTTPError as e:
                raise HTTPException(status_code=502, detail=f"Dictionary unavailable: {e}")
