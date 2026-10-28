"""Builds plants/data/plants.json from plant_list.csv by asking Trefle about each plant.

Run it on a laptop (it needs TREFLE_TOKEN in .env), never on the live site:
    python manage.py build_plant_list
"""
import csv
import json
import time
from pathlib import Path

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from plants import mapping
from plants.services import trefle
from plants.services.http import ApiError

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
PAUSE_SECONDS = 2  # Trefle allows 60 calls a minute, we use 2 per plant


def norm(name):
    return " ".join((name or "").lower().replace("×", "x").split())


def best_match(scientific_name, found):
    """Only an exact scientific name counts. 'Close enough' can be a weed (Daucus carota is a wild carrot)."""
    for item in found:
        if norm(item.get("scientific_name")) == norm(scientific_name):
            return item
    return None


def add_photo(fields, search_item):
    """Use Trefle's photo only when it says who took it and under which license."""
    image = search_item.get("main_image") or {}
    licence = image.get("licence") or ""
    if image.get("image_url") and licence.upper().startswith("CC"):
        fields["image_url"] = image["image_url"]
        fields["image_credit"] = f"Photo by {image.get('author') or 'unknown'}, {licence}"
        fields["image_credit_url"] = image.get("licence_url") or ""


class Command(BaseCommand):
    help = "Ask Trefle about every plant in plant_list.csv and save plants/data/plants.json"

    def handle(self, *args, **options):
        rows = list(csv.DictReader(open(DATA_DIR / "plant_list.csv", encoding="utf-8")))
        plants, missing = [], []
        for row in rows:
            name, scientific = row["english_name"], row["scientific_name"]
            try:
                item = best_match(scientific, trefle.search(scientific))
                if not item:
                    missing.append(name)
                    self.stdout.write(f"not found: {name} ({scientific})")
                    continue
                fields = mapping.from_trefle(trefle.species(item["id"]), row["category"], name)
            except ApiError as error:
                missing.append(name)
                self.stdout.write(f"error on {name}: {error}")
                continue
            fields["slug"] = slugify(name)
            add_photo(fields, item)
            plants.append(fields)
            self.stdout.write(f"ok: {name}")
            time.sleep(PAUSE_SECONDS)

        with open(DATA_DIR / "plants.json", "w", encoding="utf-8") as file:
            file.write(json.dumps(plants, indent=2, ensure_ascii=False) + "\n")
        with_photo = sum(1 for p in plants if p.get("image_url"))
        self.stdout.write(f"\nsaved {len(plants)} plants, {with_photo} with a licensed photo")
        if missing:
            self.stdout.write(f"missing {len(missing)}: {', '.join(missing)}")