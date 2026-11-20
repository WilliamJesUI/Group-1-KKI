import json
from pathlib import Path

from django.db import migrations

DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "plants.json"


def load_new_plants(apps, schema_editor):
    """Adds the plants from plants.json that aren't in the database yet. Plants that are already there
    stay as they are (nothing an admin changed gets overwritten), except that one with no photo gets the new one."""
    Plant = apps.get_model("plants", "Plant")
    field_names = {field.name for field in Plant._meta.get_fields()}
    slugs = set(Plant.objects.values_list("slug", flat=True))
    trefle_ids = set(Plant.objects.exclude(trefle_id=None).values_list("trefle_id", flat=True))
    for item in json.loads(DATA_FILE.read_text(encoding="utf-8")):
        if item["slug"] in slugs and item.get("image_url"):
            Plant.objects.filter(slug=item["slug"], image_url="").update(
                image_url=item["image_url"],
                image_credit=item.get("image_credit", ""),
                image_credit_url=item.get("image_credit_url", ""),
            )
        if item["slug"] in slugs or item.get("trefle_id") in trefle_ids:
            continue  # already here (trefle_id is unique, so the same species can't come in twice)
        fields = {k: v for k, v in item.items() if k in field_names and k != "id"}
        Plant.objects.create(**fields)
        slugs.add(item["slug"])
        if item.get("trefle_id"):
            trefle_ids.add(item["trefle_id"])


class Migration(migrations.Migration):

    dependencies = [
        ("plants", "0004_load_wikipedia_text"),
    ]

    operations = [
        migrations.RunPython(load_new_plants, migrations.RunPython.noop),
    ]
