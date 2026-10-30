"""Adds a small set of demo gardeners and their activity, so the site looks lived in.

    python manage.py seed_demo           # add (safe to run twice, it skips what is already there)
    python manage.py seed_demo --remove  # delete every demo gardener and everything they made

Demo gardeners can't log in (no password), and their posts are dated a few days back,
so anything a real user posts shows up above them.
"""
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from achievements.models import Goal, ProgressLog
from community.models import Answer, Question
from encyclopedia.models import PlantCollection, SavedPlant
from events.models import Event
from garden.models import Comment, Post
from plants.models import Plant

GARDENERS = [
    ("rina.grows", "Rina", "Balcony chilies and too many herbs.", "Depok"),
    ("budi_tanam", "Budi", "Weekend gardener, slowly learning tomatoes.", "Jakarta Selatan"),
    ("maya.leaf", "Maya", "Flowers on the windowsill, basil in the kitchen.", "Bogor"),
    ("dimas.soil", "Dimas", "Compost nerd. Ask me about kitchen scraps.", "Tangerang"),
    ("sari.sprout", "Sari", "First year growing anything. So far so good!", "Bekasi"),
]

POSTS = [
    ("rina.grows", "chili-pepper", "First red chili of the season! The plant is only knee high but it's full of flowers."),
    ("budi_tanam", "tomato", "Tied up the tomatoes today before the rain. Leaves look much healthier since I stopped watering at night."),
    ("maya.leaf", "sweet-basil", "Pinched the tops off the basil like someone said in Community and it got so bushy."),
    ("dimas.soil", "spinach", "Spinach from seed in three weeks. Compost from last month went right into this bed."),
    ("sari.sprout", "mint", "My mint survived the week I forgot about it. Mint is unbeatable."),
    ("maya.leaf", "marigold", "Marigolds next to the tomatoes to keep bugs away. Will report back."),
]

QUESTIONS = [
    ("sari.sprout", "mint", "Why are my mint leaves turning yellow?", "It sits by a window and I water it every day. The bottom leaves are going yellow.",
     [("dimas.soil", "Probably too much water. Let the top of the soil dry out first and make sure the pot has a drain hole.")]),
    ("budi_tanam", "tomato", "How often should I water tomatoes in pots?", "It's very hot here lately and the soil dries fast.",
     [("rina.grows", "I water mine every morning when it's hot, deep enough that water comes out the bottom."),
      ("maya.leaf", "Mulch on top helps a lot, the soil stays wet much longer.")]),
    ("maya.leaf", "sweet-basil", "Can I grow basil from cuttings?", "",
     [("rina.grows", "Yes! Put a stem in a glass of water, roots show up in about a week.")]),
]

EVENTS = [
    ("dimas.soil", "spinach", "Compost basics meetup", "Bring your kitchen scraps questions. We'll start a small compost bin together.", "Taman Menteng", 9),
    ("rina.grows", "chili-pepper", "Chili seedling swap", "Swap your extra chili seedlings and seeds with other gardeners.", "Taman Suropati", 16),
]

GOALS = [
    ("rina.grows", "chili-pepper", "Harvest 30 chilies", 30, 12),
    ("budi_tanam", "tomato", "Harvest 10 tomatoes", 10, 3),
    ("sari.sprout", "mint", "Pick mint 15 times", 15, 6),
]


class Command(BaseCommand):
    help = "Adds (or with --remove, deletes) a few demo gardeners and their posts, questions, events and goals."

    def add_arguments(self, parser):
        parser.add_argument("--remove", action="store_true", help="Delete the demo gardeners and everything they made.")

    def handle(self, *args, **options):
        names = [g[0] for g in GARDENERS]
        if options["remove"]:
            count, _ = User.objects.filter(username__in=names).delete()
            self.stdout.write(self.style.SUCCESS(f"Removed the demo gardeners ({count} rows)."))
            return
        with transaction.atomic():
            self.seed()
        self.stdout.write(self.style.SUCCESS("Demo gardeners are ready."))

    def seed(self):
        plants = {p.slug: p for p in Plant.objects.all()}
        users = {}
        for username, first_name, bio, location in GARDENERS:
            user, created = User.objects.get_or_create(username=username, defaults={"first_name": first_name})
            if created:
                user.set_unusable_password()
                user.save()
                profile = user.profile
                profile.bio, profile.location = bio, location
                profile.save()
            users[username] = user

        # Only add each kind of thing once, so running the command again changes nothing
        now = timezone.now()
        if not Post.objects.filter(author__in=users.values()).exists():
            for days, (author, slug, caption) in enumerate(POSTS, start=2):
                post = Post.objects.create(author=users[author], plant=plants.get(slug), caption=caption)
                Post.objects.filter(pk=post.pk).update(created_at=now - timedelta(days=days))
                post.likes.add(*[u for name, u in users.items() if name != author][:days % 4 + 1])
            first = Post.objects.filter(author__in=users.values()).order_by("-created_at").first()
            Comment.objects.create(post=first, author=users["sari.sprout"], text="Looks great! How long did it take?")

        if not Question.objects.filter(author__in=users.values()).exists():
            for days, (author, slug, title, body, answers) in enumerate(QUESTIONS, start=3):
                question = Question.objects.create(author=users[author], plant=plants.get(slug), title=title, body=body)
                Question.objects.filter(pk=question.pk).update(created_at=now - timedelta(days=days))
                for answer_author, text in answers:
                    Answer.objects.create(question=question, author=users[answer_author], body=text)

        if not Event.objects.filter(host__in=users.values()).exists():
            for host, slug, name, description, location, days_ahead in EVENTS:
                start = (now + timedelta(days=days_ahead)).replace(hour=2, minute=0, second=0, microsecond=0)  # 09:00 WIB
                event = Event.objects.create(host=users[host], theme_plant=plants.get(slug), name=name, description=description,
                                             location=location, start_time=start, end_time=start + timedelta(hours=2))
                event.attendees.add(*list(users.values())[:3])

        if not Goal.objects.filter(user__in=users.values()).exists():
            for username, slug, title, target, done in GOALS:
                if slug in plants:
                    goal = Goal.objects.create(user=users[username], plant=plants[slug], title=title, target=target)
                    ProgressLog.objects.create(goal=goal, amount=done)

        for username in ("maya.leaf", "rina.grows"):
            for slug in ("sweet-basil", "chili-pepper", "mint"):
                if slug in plants:
                    SavedPlant.objects.get_or_create(user=users[username], plant=plants[slug])
        collection, _ = PlantCollection.objects.get_or_create(user=users["maya.leaf"], name="Kitchen window")
        collection.plants.add(*[plants[s] for s in ("sweet-basil", "mint") if s in plants])
