"""Adds a short Wikipedia description to every plant in plants/data/plants.json.

Run it on a laptop after build_plant_list, never on the live site:
    python manage.py add_wikipedia_text
It only changes "description" and "description_url", so the Trefle care info stays the same.
"""
import json
import time
from pathlib import Path

from django.core.management.base import BaseCommand

from plants.services import wikipedia

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
PAUSE_SECONDS = 1  # be polite, Wikipedia asks for slow scripts


class Command(BaseCommand):
    help = "Add a Wikipedia description to every plant in plants/data/plants.json"

    def handle(self, *args, **options):
        path = DATA_DIR / "plants.json"
        plants = json.loads(path.read_text(encoding="utf-8"))
        missing = []
        for plant in plants:
            # The scientific name finds the right page ("Mentha"), the English one can be a list page ("Mint")
            found = wikipedia.summary(plant.get("scientific_name")) or wikipedia.summary(plant["name"])
            if found:
                plant["description"] = found["text"]
                plant["description_url"] = found["url"]
                self.stdout.write(f"ok: {plant['name']}")
            else:
                missing.append(plant["name"])
                self.stdout.write(f"not found: {plant['name']}")
            time.sleep(PAUSE_SECONDS)

        path.write_text(json.dumps(plants, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        self.stdout.write(f"\nadded {len(plants) - len(missing)} descriptions")
        if missing:
            self.stdout.write(f"missing {len(missing)}: {', '.join(missing)}")