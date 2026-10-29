import django.db.models.deletion
from django.db import migrations, models


def link_plant_tags(apps, schema_editor):
    # Old posts had the plant as free text (plant_tag). Link each one to the plant with that name or slug,
    # ignoring upper/lower case. Tags that match no plant are dropped, the post itself stays.
    Post = apps.get_model("garden", "Post")
    Plant = apps.get_model("plants", "Plant")
    plants = {}
    for plant in Plant.objects.all():
        plants[plant.name.casefold()] = plant
        plants[plant.slug.casefold()] = plant
    for post in Post.objects.exclude(plant_tag=""):
        plant = plants.get(post.plant_tag.strip().casefold())
        if plant:
            post.plant = plant
            post.save(update_fields=["plant"])


class Migration(migrations.Migration):

    dependencies = [
        ("garden", "0014_post_category"),
        ("plants", "0004_load_wikipedia_text"),
    ]

    operations = [
        # 1. Posts: link to the shared Plant table, add an uploaded photo
        migrations.AddField(
            model_name="post",
            name="plant",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="garden_posts", to="plants.plant"),
        ),
        migrations.RunPython(link_plant_tags, migrations.RunPython.noop),
        migrations.RemoveField(model_name="post", name="plant_tag"),
        # The category now comes from the plant (plant.category), so these two aren't needed anymore
        migrations.RemoveField(model_name="post", name="category"),
        migrations.RemoveField(model_name="post", name="categories"),
        migrations.AddField(model_name="post", name="photo", field=models.BinaryField(blank=True, null=True)),
        migrations.AddField(model_name="post", name="photo_type", field=models.CharField(blank=True, max_length=20)),
        migrations.AddField(model_name="post", name="updated_at", field=models.DateTimeField(auto_now=True)),
        migrations.AlterField(model_name="post", name="caption", field=models.TextField(max_length=1000)),
        migrations.AlterField(model_name="comment", name="text", field=models.TextField(max_length=1000)),
        migrations.AlterModelOptions(name="comment", options={"ordering": ["created_at"]}),
        # 2. Plant of the week: a pick from the Plant table instead of a typed-in copy.
        # The old rows were typed-in copies with no link to a plant, so the table starts fresh.
        migrations.DeleteModel(name="PlantOfTheWeek"),
        migrations.CreateModel(
            name="PlantOfTheWeek",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("short_line", models.CharField(blank=True, max_length=200)),
                ("chosen_at", models.DateTimeField(auto_now_add=True)),
                ("plant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="weekly_picks", to="plants.plant")),
            ],
            options={"ordering": ["-chosen_at"], "verbose_name_plural": "plants of the week"},
        ),
    ]
