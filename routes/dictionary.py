# routes/dictionary.py
from fastapi import APIRouter, HTTPException
import httpx

router = APIRouter(prefix="/dictionary", tags=["dictionary"])

# ✅ Correct base URL
FREE_DICTIONARY_API = "https://api.freedictionary.dev/api/v1/entries/en"

@router.get("/{word}")
async def lookup_word(word: str):
    """Proxy for freedictionaryapi.dev — avoids CORS issues."""
    async with httpx.AsyncClient(timeout=12) as client:
        for attempt in range(2):
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
