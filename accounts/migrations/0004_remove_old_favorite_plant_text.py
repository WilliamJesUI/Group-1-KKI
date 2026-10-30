from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_favorite_plant_from_list"),
    ]

    operations = [
        migrations.RemoveField(model_name="profile", name="favorite_plant_text"),
    ]
