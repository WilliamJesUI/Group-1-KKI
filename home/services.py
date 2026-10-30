"""Everything the landing page shows, read from the other modules.

Every function here only reads. Each one is wrapped in safely(), so if one module's table is missing or broken,
only that part of the landing page shows its empty state and the rest of the page still works.
"""
import logging
from datetime import timedelta

from django.contrib.auth.models import User
from django.db import DatabaseError
from django.db.models import Count, Exists, OuterRef, Prefetch, Q, Sum
from django.utils import timezone

from achievements.models import ClaimedBadge, Goal, Milestone
from community.models import Answer, Question
from encyclopedia.models import PlantCollection
from events.models import Event
from events.views import mark_going
from garden.models import Post, short_age
from garden.views import get_plant_of_the_week
from plants.models import Plant

logger = logging.getLogger(__name__)

SHELF_SIZE = 12
# The pills above the plant shelf: (value in ?shelf=, label). The values match Plant.category.
SHELF_PILLS = [("all", "All plants"), ("vegetables", "Vegetables"), ("herbs", "Herbs"), ("flowers", "Flowers")]


def safely(build, fallback):
    """Run build(). If the database fails, log it and give back fallback instead of breaking the page."""
    try:
        return build()
    except DatabaseError:
        logger.exception("Landing page: one section could not be loaded")
        return fallback


def ago(moment):
    """short_age from the Garden with "ago" when it reads right: "2 hr ago", but "just now" and "7 Nov" stay."""
    age = short_age(moment)
    return f"{age} ago" if age.endswith(("min", "hr", " d")) else age


def week_ago():
    return timezone.now() - timedelta(days=7)


def site_numbers():
    """The 4 numbers next to "In this issue"."""
    return {
        "plants": Plant.objects.count(),
        "events": Event.objects.filter(start_time__gte=timezone.now()).count(),
        "posts": Post.objects.count(),
        "gardeners": User.objects.filter(is_active=True).count(),
        "open_questions": Question.objects.filter(answers__isnull=True).count(),
        "badges": Milestone.objects.count(),
    }


def posters_this_week():
    """How many different people posted in the Garden in the last 7 days (the live line at the top)."""
    return Post.objects.filter(created_at__gte=week_ago()).values("author").distinct().count()


def garden_posts(user):
    """The most liked post with a photo from this week (or the newest one), plus the 2 newest other posts.
    Annotated like the Garden feed, so garden/post_card.html (and its AJAX like button) works here too."""
    posts = (
        Post.objects.defer("photo")
        .select_related("author__profile", "plant")
        .annotate(like_count=Count("likes", distinct=True), comment_count=Count("comments", distinct=True))
        .filter(Q(photo_type__gt="") | Q(image_url__gt=""))
    )
    if user.is_authenticated:
        posts = posts.annotate(is_liked=Exists(Post.likes.through.objects.filter(post=OuterRef("pk"), user=user)))
    top = posts.filter(created_at__gte=week_ago()).order_by("-like_count", "-created_at").first() or posts.first()
    if top is None:
        return None, []
    return top, list(posts.exclude(pk=top.pk)[:2])


def upcoming_events(user):
    """The next 3 events. The first one is the big poster, the other 2 use events/event_cards.html.
    mark_going (from the Events page) sets is_going and the card avatars."""
    events = list(
        Event.objects.defer("cover_image")
        .filter(start_time__gte=timezone.now())
        .select_related("theme_plant")
        .annotate(going_count=Count("attendees"))
        .prefetch_related(Prefetch("attendees", queryset=User.objects.select_related("profile").order_by("pk")))
        .order_by("start_time")[:3]
    )
    mark_going(events, user)
    for event in events:
        event.faces = list(event.attendees.all()[:4])
    return events


def plant_of_the_week():
    plant, short_line = get_plant_of_the_week()
    return {"plant": plant, "short_line": short_line}


def plant_shelf(category, first=None):
    """12 plants with a photo for the sideways shelf. The plant of the week goes first when it fits the pill."""
    plants = Plant.objects.exclude(image_url="").order_by("name")
    if category != "all":
        plants = plants.filter(category=category)
    shelf = list(plants[:SHELF_SIZE])
    if first is not None and first in plants and first not in shelf[:1]:
        shelf = [first] + [plant for plant in shelf if plant != first][: SHELF_SIZE - 1]
    return shelf


def newest_questions():
    """The newest question (shown as a big quote) and the 2 before it."""
    questions = list(
        Question.objects.select_related("author__profile", "plant")
        .annotate(answer_count=Count("answers", distinct=True), vote_count=Count("voters", distinct=True))
        .order_by("-created_at")[:3]
    )
    for question in questions:
        question.age = ago(question.created_at)
    return questions


def badges():
    """The 4 badges people claimed the most, and the newest claim ("Mira earned First Harvest")."""
    top = list(Milestone.objects.annotate(earned=Count("claims")).order_by("-earned", "order")[:4])
    gardeners = User.objects.filter(is_active=True).count()
    for badge in top:
        badge.gardeners = gardeners
        badge.percent = round(badge.earned * 100 / gardeners) if gardeners else 0
    latest = ClaimedBadge.objects.select_related("user", "milestone").order_by("-claimed_at").first()
    if latest:
        latest.age = ago(latest.claimed_at)
    return {"top": top, "latest": latest}


def your_week(user):
    """The personal counts and goals for a logged-in user. Everything counts from 7 days ago, not from
    last_login, because Django changes last_login the moment you log in."""
    since = week_ago()
    goals = list(Goal.objects.filter(user=user).annotate(total_done=Sum("logs__amount")).order_by("-updated_at"))
    for goal in goals:
        goal.total_done = goal.total_done or 0
    return {
        "new_posts": Post.objects.filter(created_at__gte=since).exclude(author=user).count(),
        "new_events": Event.objects.filter(created_at__gte=since).exclude(host=user).count(),
        "going": user.rsvped_events.filter(start_time__gte=timezone.now()).count(),
        "saved": PlantCollection.objects.filter(user=user, plants__isnull=False).values("plants").distinct().count(),
        "answers_for_you": Answer.objects.filter(question__author=user, created_at__gte=since).exclude(author=user).count(),
        "goals": goals[:2],
        "goals_done": sum(goal.is_complete for goal in goals),
        "goal_count": len(goals),
    }


def numbers_list(numbers):
    """The numbers next to "In this issue" as (value, label) pairs, so the template can loop over them."""
    if not numbers:
        return []
    return [
        (numbers["plants"], "plants"),
        (numbers["events"], "events"),
        (numbers["posts"], "posts"),
        (numbers["gardeners"], "gardeners"),
    ]


def contents(numbers, next_event=None, mine=None):
    """The 5 rows of "In this issue", one per module (Figma "In this issue"). The chip on the right is personal
    when logged in."""
    numbers = numbers or {}

    def count(value, word):
        return f"{value} {word}{'' if value == 1 else 's'}"

    plants = numbers.get("plants", 0)
    next_chip = f"Next: {next_event.start_time:%a} {next_event.start_time.day} {next_event.start_time:%b}" if next_event else "No events yet"
    rows = [
        ("garden", "Garden", "Photos and tips from your neighbors' plots.", count(numbers.get("posts", 0), "post"), "bg-brand-soft"),
        ("events", "Events", "Seed swaps, planting days and workshops nearby.", next_chip, "bg-butter"),
        ("encyclopedia", "Encyclopedia", f"How to grow {plants} vegetables, herbs and flowers.", count(plants, "plant"), "bg-brand-soft"),
        ("community", "Community", "Ask a question, get answers from real gardeners.",
         count(numbers.get("open_questions", 0), "open question"), "bg-pink"),
        ("achievements", "Achievements", "Set growing goals and collect badges.", count(numbers.get("badges", 0), "badge"), "bg-lilac"),
    ]
    if mine:
        personal = {
            "garden": f"{mine['new_posts']} new this week",
            "events": "Going to " + count(mine["going"], "event"),
            "encyclopedia": f"{mine['saved']} saved",
            "community": count(mine["answers_for_you"], "answer") + " for you",
            "achievements": f"{mine['goals_done']} of {mine['goal_count']} goals" if mine["goal_count"] else "Set your first goal",
        }
        rows = [(slug, name, line, personal[slug], tint) for slug, name, line, _, tint in rows]
    return [
        {"number": f"{index:02}", "slug": slug, "name": name, "line": line, "chip": chip, "tint": tint}
        for index, (slug, name, line, chip, tint) in enumerate(rows, start=1)
    ]
