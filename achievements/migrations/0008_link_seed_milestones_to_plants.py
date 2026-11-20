from django.db import migrations


def link_seed_milestones(apps, schema_editor):
    Milestone = apps.get_model("achievements", "Milestone")
    Plant = apps.get_model("plants", "Plant")

    # Carry forward the old tomato-specific filter using the actual Plant row.
    tomato = Plant.objects.filter(slug="tomato").first()
    if tomato:
        Milestone.objects.filter(slug="tomato-time", plant__isnull=True).update(plant=tomato)


class Migration(migrations.Migration):
    dependencies = [
        ("achievements", "0007_remove_milestone_plant_type_milestone_plant"),
        ("plants", "0004_load_wikipedia_text"),
    ]

    operations = [
        migrations.RunPython(link_seed_milestones, migrations.RunPython.noop),
    ]
