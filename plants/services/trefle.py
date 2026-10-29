from django.conf import settings
from django.core.cache import cache

from .http import ApiError, get_json

BASE_URL = "https://trefle.io/api/v1"
ONE_DAY = 60 * 60 * 24


def _get(path, params=None):
    token = settings.TREFLE_TOKEN
    if not token:
        raise ApiError("TREFLE_TOKEN is not set")
    return get_json(f"{BASE_URL}{path}", params={**(params or {}), "token": token})


def search(query):
    """Species matching a name. Saved for a day so the same search doesn't use up our 60 calls a minute."""
    key = "trefle:search:" + query.lower().strip().replace(" ", "_")
    results = cache.get(key)
    if results is None:
        # /species/search, not /plants/search: the ids it gives are the ones /species/<id> expects
        results = _get("/species/search", {"q": query}).get("data", [])
        cache.set(key, results, ONE_DAY)
    return results


def species(trefle_id):
    """Full details for one plant (growth, flower, duration, images...)."""
    key = f"trefle:species:{trefle_id}"
    data = cache.get(key)
    if data is None:
        data = _get(f"/species/{trefle_id}").get("data", {})
        cache.set(key, data, ONE_DAY)
    return data