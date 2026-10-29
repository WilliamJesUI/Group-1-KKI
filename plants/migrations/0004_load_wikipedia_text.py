import json
from pathlib import Path

from django.db import migrations

DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "plants.json"


def load_descriptions(apps, schema_editor):
    """Copies only the Wikipedia text from plants.json, so nothing else on the plants changes."""
    Plant = apps.get_model("plants", "Plant")
    for item in json.loads(DATA_FILE.read_text(encoding="utf-8")):
        if item.get("description"):
            Plant.objects.filter(slug=item["slug"]).update(
                description=item["description"],
                description_url=item.get("description_url", ""),
            )


class Migration(migrations.Migration):

    dependencies = [
        ("plants", "0003_load_starter_plants"),
    ]

    operations = [
        migrations.RunPython(load_descriptions, migrations.RunPython.noop),
    ]