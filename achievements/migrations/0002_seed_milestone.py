from django.db import migrations

# The starting milestones (the four from Figma plus two plant-specific ones).
# Edit or add more in the admin at /admin/achievements/milestone/
MILESTONES = [
    ("first-sprout", "First Sprout", "Add your first plant", "plants_added", 1, "img/icons/ach-sprout-lg.svg", "bg-brand-soft", "", 1),
    ("first-harvest", "First Harvest", "Log your first harvest", "harvests_logged", 1, "img/icons/ach-award-lg.svg", "bg-pink", "", 2),
    ("seven-day-streak", "7 Day Streak", "Check in for seven days", "checkin_streak", 7, "img/icons/ach-calendar-lg.svg", "bg-lilac", "", 3),
    ("good-neighbor", "Good Neighbor", "Answer 10 questions", "answers_given", 10, "img/icons/ach-users-lg.svg", "bg-[#b8fff8]", "", 4),
    ("tomato-time", "Tomato Time", "Log 3 tomato harvests", "harvests_logged", 3, "img/icons/ach-award-lg.svg", "bg-pink", "tomato", 5),
    ("herb-garden", "Herb Garden", "Add 3 herbs to your garden", "plants_added", 3, "img/icons/ach-sprout-lg.svg", "bg-brand-soft", "herbs", 6),
]


def seed(apps, schema_editor):
    Milestone = apps.get_model("achievements", "Milestone")
    for slug, title, description, metric, target, icon, tone, plant_type, order in MILESTONES:
        Milestone.objects.update_or_create(slug=slug, defaults={
            "title": title, "description": description, "metric": metric, "target": target,
            "icon": icon, "tone": tone, "plant_type": plant_type, "order": order,
        })


class Migration(migrations.Migration):
    dependencies = [("achievements", "0001_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]