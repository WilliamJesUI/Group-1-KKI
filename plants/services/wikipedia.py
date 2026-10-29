"""Short English descriptions from Wikipedia.

Docs: https://en.wikipedia.org/api/rest_v1/
Wikipedia text is CC BY-SA, so wherever we show it we link back to the article (description_url).
"""
from urllib.parse import quote

from .http import ApiError, get_json

SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/"


def summary(title):
    """Returns {"text", "url"} for a Wikipedia page, or None if there's no normal page."""
    if not title:
        return None
    try:
        data = get_json(SUMMARY_URL + quote(title.replace(" ", "_")))
    except ApiError:
        return None
    # "disambiguation" pages list many meanings ("Mint" the herb, the coin place...), so skip them
    if data.get("type") != "standard" or not data.get("extract"):
        return None
    return {
        "text": first_sentences(data["extract"], 2),
        "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
    }


def first_sentences(text, count):
    # Good enough for Wikipedia intros. Splits on ". " so a name like "St. John's wort" can cut early,
    # which is why we keep the full text if the cut one is very short.
    parts = text.split(". ")
    short = ". ".join(parts[:count]).strip()
    if not short.endswith("."):
        short += "."
    return short if len(short) > 40 else text