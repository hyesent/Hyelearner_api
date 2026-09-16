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
    """
    Convert Suvankar's response into the format
    HyeLearner's existing Dictionary page expects.
    """

    meanings = []
    phonetics = []
    source_urls = []

    entries = data if isinstance(data, list) else data.get("definitions", data)

    if isinstance(entries, dict):
        entries = [entries]

    for entry in entries or []:
        part_of_speech = (
            entry.get("partOfSpeech")
            or entry.get("part_of_speech")
            or entry.get("pos")
            or ""
        )

        definitions = []

        raw_definitions = (
            entry.get("definitions")
            or entry.get("definition")
            or []
        )

        if isinstance(raw_definitions, str):
            raw_definitions = [{"definition": raw_definitions}]

        for item in raw_definitions:
            if isinstance(item, str):
                definitions.append({
                    "definition": item,
                    "example": None,
                    "synonyms": [],
                    "antonyms": []
                })
                continue

            definitions.append({
                "definition": item.get("definition", ""),
                "example": item.get("example"),
                "synonyms": item.get("synonyms", []) or [],
                "antonyms": item.get("antonyms", []) or []
            })

        if definitions:
            meanings.append({
                "partOfSpeech": part_of_speech,
                "definitions": definitions
            })

        pronunciation = (
            entry.get("pronunciation")
            or entry.get("phonetic")
        )

        if pronunciation:
            if isinstance(pronunciation, str):
                phonetics.append({
                    "text": pronunciation,
                    "audio": ""
                })
            elif isinstance(pronunciation, dict):
                phonetics.append({
                    "text": pronunciation.get("text")
                    or pronunciation.get("ipa")
                    or "",
                    "audio": pronunciation.get("audio") or ""
                })

        urls = entry.get("sourceUrls") or entry.get("source_urls") or []

        if isinstance(urls, str):
            urls = [urls]

        source_urls.extend(urls)

    return {
        "word": data.get("word", word) if isinstance(data, dict) else word,
        "phonetic": (
            phonetics[0]["text"]
            if phonetics
            else ""
        ),
        "phonetics": phonetics,
        "meanings": meanings,
        "sourceUrls": list(dict.fromkeys(source_urls))
    }
