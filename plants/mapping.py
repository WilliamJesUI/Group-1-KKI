"""Turns Trefle's numbers into the words Figma shows (Full sun, Frequent...).

Trefle's light goes from 1 (deep shade) to 9 (full sun). It has no watering info for
garden plants, so watering comes from simple rules. If a rule gets one plant wrong,
fix that plant in the admin page.
"""

HERB_FAMILIES = {"Lamiaceae", "Apiaceae"}  # basil, mint, rosemary, parsley, coriander...
SUCCULENT_FAMILIES = {"Asphodelaceae", "Cactaceae", "Crassulaceae"}  # store water, need the least
WOODY_HABITS = {"Shrub", "Subshrub", "Tree"}
WATERING_DAYS = {"frequent": "2-3 days", "average": "5-7 days", "minimum": "10-14 days"}


def growth_habit(species):
    # Trefle gives a list like "Subshrub, Forb/herb". The first one is the main one.
    text = (species.get("specifications") or {}).get("growth_habit") or ""
    return text.split(",")[0].strip()


def is_woody(species):
    return growth_habit(species) in WOODY_HABITS


def sunlight_for(species):
    """Returns (value, estimated)."""
    light = (species.get("growth") or {}).get("light")
    if light is None:
        return "full_sun", True  # most plants in our list want sun, so it's the safe guess
    if light >= 8:
        return "full_sun", False
    if light >= 6:
        return "full_sun_part_shade", False  # Trefle's 7 means "mostly full light, also partial shade"
    if light >= 4:
        return "part_shade", False
    return "shade", False


def watering_for(species, category):
    """Returns (value, estimated)."""
    if species.get("family") in SUCCULENT_FAMILIES:
        return "minimum", True
    if is_woody(species):
        # woody herbs (rosemary, thyme) like to dry out, woody flowers (roses) are in between
        return ("minimum" if category == "herbs" else "average"), True
    if category in ("vegetables", "herbs"):
        return "frequent", True  # soft veg and leafy herbs dry out fast in Jakarta's heat
    return "average", True


def cycle_for(species):
    for value in species.get("duration") or []:
        if value in ("annual", "biennial", "perennial"):
            return value
    return ""


def difficulty_for(species, category, cycle):
    # Woody or slow plants take more care. Quick annuals and soft veg and herbs are easy.
    slow = ((species.get("specifications") or {}).get("growth_rate") or "").lower() == "slow"
    if is_woody(species) or slow:
        return "medium"
    if cycle in ("annual", "biennial") or category in ("vegetables", "herbs"):
        return "easy"
    return "medium"


def from_trefle(species, category, name):
    """Our Plant fields for one Trefle species. category and name come from our own plant list."""
    cycle = cycle_for(species)
    sunlight, sun_guessed = sunlight_for(species)
    watering, water_guessed = watering_for(species, category)
    return {
        "name": name,
        "scientific_name": species.get("scientific_name") or "",
        "family": species.get("family") or "",
        "category": category,
        "sunlight": sunlight,
        "watering": watering,
        "watering_every": WATERING_DAYS[watering],
        "cycle": cycle,
        "difficulty": difficulty_for(species, category, cycle),
        "care_estimated": sun_guessed or water_guessed,
        "trefle_id": species.get("id"),
        "info_source": "Trefle",
    }