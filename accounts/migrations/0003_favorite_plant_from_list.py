import django.db.models.deletion
from django.db import migrations, models


def match_old_text_to_plants(apps, schema_editor):
    """Profiles that typed a plant name before (like "Cherry Tomato") get the plant with that name, if there is one."""
    Profile = apps.get_model("accounts", "Profile")
    Plant = apps.get_model("plants", "Plant")
    for profile in Profile.objects.exclude(favorite_plant_text=""):
        plant = Plant.objects.filter(name__iexact=profile.favorite_plant_text.strip()).first()
        if plant:
            profile.favorite_plant = plant
            profile.save(update_fields=["favorite_plant"])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_profile_avatar_color"),
        ("plants", "0004_load_wikipedia_text"),
    ]

    operations = [
        # The old text column gets a new name, so the new link can take the name "favorite_plant"
        migrations.RenameField(model_name="profile", old_name="favorite_plant", new_name="favorite_plant_text"),
        migrations.AddField(
            model_name="profile",
            name="favorite_plant",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="favorited_by", to="plants.plant",
            ),
        ),
        migrations.RunPython(match_old_text_to_plants, migrations.RunPython.noop),
    ]
