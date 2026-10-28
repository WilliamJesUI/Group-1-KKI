from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from achievements.models import ClaimedBadge, Milestone
from achievements.services import build_milestones, can_claim, check_in_today, get_metric

PLANT_FILTERS = [(value, label) for value, label in Milestone.PLANT_CHOICES]


def show_achievements(request):
    user = request.user
    plant = request.GET.get("plant", "")
    if plant not in dict(PLANT_FILTERS):
        plant = ""

    cards = build_milestones(user)
    total = len(cards)
    unlocked = sum(1 for card in cards if card["claimed"])
    in_progress = sum(1 for card in cards if not card["claimed"] and card["percent"] > 0)
    shown = [card for card in cards if not plant or card["milestone"].plant_type == plant]

    context = {
        "unlocked": unlocked,
        "total": total,
        "remaining": total - unlocked,
        "progress_percent": unlocked * 100 // total if total else 0,
        "milestones_in_progress": in_progress,
        "stats": [
            {"icon": "img/icons/ach-award.svg", "value": unlocked, "label": "Badges unlocked"},
            {"icon": "img/icons/ach-sprout.svg", "value": get_metric(user, "checkin_streak"), "label": "Day garden streak"},
            {"icon": "img/icons/ach-leaf.svg", "value": get_metric(user, "plants_thriving"), "label": "Plants thriving"},
            {"icon": "img/icons/ach-users.svg", "value": get_metric(user, "posts_shared"), "label": "Posts shared"},
        ],
        "cards": shown,
        "plant_filters": PLANT_FILTERS,
        "selected_plant": plant,
    }
    return render(request, "achievements.html", context)


@require_POST
def claim_badge(request, slug):
    milestone = get_object_or_404(Milestone, slug=slug)
    if not request.user.is_authenticated:
        messages.error(request, "Log in first\nYou need an account to claim badges.")
    elif not can_claim(request.user, milestone):
        messages.error(request, "Not ready yet\nFinish the milestone first, or you already claimed this badge.")
    else:
        ClaimedBadge.objects.get_or_create(user=request.user, milestone=milestone)
        messages.success(request, f"Badge claimed\nYou unlocked {milestone.title}.")
    return redirect("achievements:show_achievements")


@require_POST
def check_in(request):
    if not request.user.is_authenticated:
        messages.error(request, "Log in first\nYou need an account to check in.")
    elif check_in_today(request.user):
        messages.success(request, "Checked in\nSee you in the garden tomorrow.")
    else:
        messages.success(request, "Already checked in\nCome back tomorrow to keep your streak.")
    return redirect("achievements:show_achievements")