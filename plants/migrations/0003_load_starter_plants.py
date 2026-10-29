import json
from pathlib import Path

from django.db import migrations

DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "plants.json"


def load_plants(apps, schema_editor):
    Plant = apps.get_model("plants", "Plant")
    field_names = {field.name for field in Plant._meta.get_fields()}
    for item in json.loads(DATA_FILE.read_text(encoding="utf-8")):
        fields = {k: v for k, v in item.items() if k in field_names and k not in ("id", "slug")}
        Plant.objects.update_or_create(slug=item["slug"], defaults=fields)


class Migration(migrations.Migration):

    dependencies = [
        ("plants", "0002_plant_care_estimated_plant_cycle_and_more"),
    ]

    operations = [
        migrations.RunPython(load_plants, migrations.RunPython.noop),
    ]