# routes/dictionary.py
from fastapi import APIRouter, HTTPException
import httpx

router = APIRouter(prefix="/dictionary", tags=["dictionary"])

DICTIONARY_API = "https://api.dictionaryapi.dev/api/v2/entries/en"

@router.get("/{word}")
async def lookup_word(word: str):
    """Proxy for dictionaryapi.dev — avoids CORS issues in the browser."""
    async with httpx.AsyncClient(timeout=8) as client:
        try:
            r = await client.get(f"{DICTIONARY_API}/{word}")
            if r.status_code == 404:
                raise HTTPException(status_code=404, detail="Word not found")
            r.raise_for_status()
            return r.json()
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Dictionary timed out")
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Dictionary unavailable: {e}")
