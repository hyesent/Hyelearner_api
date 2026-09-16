# routes/dictionary.py

from fastapi import APIRouter, HTTPException
import httpx

router = APIRouter(
    prefix="/dictionary",
    tags=["dictionary"]
)

DICTIONARY_API = "https://api.suvankar.cc/dictionaryapi/v1/definitions/en"


@router.get("/{word}")
async def lookup_word(word: str):
    """Proxy for Suvankar Free Dictionary API."""

    word = word.strip().lower()

    if not word:
        raise HTTPException(
            status_code=400,
            detail="Word is required"
        )

    url = f"{DICTIONARY_API}/{word}?compact=true"

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            response = await client.get(url)

            if response.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail="Word not found"
                )

            response.raise_for_status()

            data = response.json()

            return normalize_dictionary_response(data, word)

        except HTTPException:
            raise

        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail="Dictionary timed out"
            )

        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=502,
                detail=f"Dictionary unavailable: {str(e)}"
            )


def normalize_dictionary_response(data, word: str):
    """Convert Suvankar/Wiktionary data to HyeLearner's format."""

    if not isinstance(data, dict):
        return {
            "word": word,
            "phonetic": "",
            "phonetics": [],
            "meanings": [],
            "sourceUrls": []
        }

    meanings = []

    for meaning in data.get("meanings", []):
        part_of_speech = meaning.get("partOfSpeech", "")
        definitions = []

        for sense in meaning.get("senses", []):
            for gloss in sense.get("glosses", []):
                definitions.append({
                    "definition": gloss,
                    "example": None,
                    "synonyms": [],
                    "antonyms": []
                })

        if definitions:
            meanings.append({
                "partOfSpeech": part_of_speech,
                "definitions": definitions
            })

    phonetics = []

    raw_phonetics = data.get("phonetics", [])

    if isinstance(raw_phonetics, list):
        for phonetic in raw_phonetics:
            if isinstance(phonetic, dict):
                phonetics.append({
                    "text": (
                        phonetic.get("text")
                        or phonetic.get("ipa")
                        or ""
                    ),
                    "audio": phonetic.get("audio") or ""
                })

    phonetic = data.get("phonetic", "")

    if not phonetic and phonetics:
        phonetic = phonetics[0].get("text", "")

    return {
        "word": data.get("word", word),
        "phonetic": phonetic,
        "phonetics": phonetics,
        "meanings": meanings,
        "sourceUrls": data.get("sourceUrls", [])
    }
