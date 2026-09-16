# routes/dictionary.py

from fastapi import APIRouter, HTTPException
import httpx

router = APIRouter(
    prefix="/dictionary",
    tags=["dictionary"]
)

FREE_DICTIONARY_API = "https://api.dictionaryapi.dev/api/v2/entries/en"


@router.get("/{word}")
async def lookup_word(word: str):
    """Proxy for Free Dictionary API — avoids CORS issues."""

    word = word.strip().lower()

    if not word:
        raise HTTPException(
            status_code=400,
            detail="Word is required"
        )

    async with httpx.AsyncClient(timeout=12) as client:
        for attempt in range(2):
            try:
                response = await client.get(
                    f"{FREE_DICTIONARY_API}/{word}"
                )

                if response.status_code == 404:
                    raise HTTPException(
                        status_code=404,
                        detail="Word not found"
                    )

                response.raise_for_status()

                return response.json()

            except HTTPException:
                raise

            except httpx.TimeoutException:
                if attempt == 1:
                    raise HTTPException(
                        status_code=504,
                        detail="Dictionary timed out"
                    )

            except httpx.HTTPError as e:
                if attempt == 1:
                    raise HTTPException(
                        status_code=502,
                        detail=f"Dictionary unavailable: {str(e)}"
                    )
