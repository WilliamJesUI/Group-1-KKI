import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("plants", "0003_load_starter_plants"),
    ]

    operations = [
        migrations.CreateModel(
            name="PlantCollection",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(default="My Balcony", max_length=100)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "plants",
                    models.ManyToManyField(
                        blank=True,
                        related_name="collections",
                        to="plants.plant",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="plant_collections",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="SavedPlant",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("saved_at", models.DateTimeField(auto_now_add=True)),
                (
                    "plant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="saved_by",
                        to="plants.plant",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="saved_plants",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-saved_at"]},
        ),
        migrations.AddConstraint(
            model_name="savedplant",
            constraint=models.UniqueConstraint(
                fields=("user", "plant"),
                name="unique_saved_plant_per_user",
            ),
        ),
    ]
