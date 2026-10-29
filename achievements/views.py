from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from achievements.forms import GoalForm, ProgressLogForm
from achievements.models import ClaimedBadge, Goal, Milestone
from achievements.services import build_milestones, can_claim, check_in_today, get_metric

PLANT_FILTERS = [(value, label) for value, label in Milestone.PLANT_CHOICES]


# ensure_csrf_cookie: the goal pop-ups use fetch, which needs the csrftoken cookie
@ensure_csrf_cookie
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
        # total_done adds up the logs of every goal in one query, Goal.done uses it
        "goals": list(
            Goal.objects.filter(user=user).annotate(total_done=Coalesce(Sum("logs__amount"), 0))
        ) if user.is_authenticated else [],
        # Empty forms for the "Start a goal", "Edit goal" and "Log progress" pop-ups
        "goal_form": GoalForm(),
        "log_form": ProgressLogForm(),
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


def get_own_goal(request, goal_id):
    # Returns (goal, None) for the goal's owner, or (None, error response) for everyone else.
    # Hiding the buttons isn't enough, anyone could send these requests with fetch, so every view checks.
    if not request.user.is_authenticated:
        return None, JsonResponse({"message": "Please log in to manage your goals."}, status=403)
    goal = get_object_or_404(Goal, pk=goal_id)
    if goal.user != request.user:
        return None, JsonResponse({"message": "This isn't your goal."}, status=403)
    return goal, None


@require_POST
def create_goal_ajax(request):
    # Not @login_required: for fetch requests we want a JSON error, not a redirect to a login page
    if not request.user.is_authenticated:
        return JsonResponse({"message": "Please log in to start a goal."}, status=403)
    form = GoalForm(request.POST)
    if form.is_valid():
        goal = form.save(commit=False)
        goal.user = request.user
        goal.save()
        # The text before \n is the toast's title, the rest is the smaller message under it
        messages.success(request, "Goal started\nLog progress on it whenever you can.")
        return JsonResponse({"id": goal.id}, status=201)
    return JsonResponse({"errors": form.errors.get_json_data()}, status=400)


@require_POST
def edit_goal_ajax(request, goal_id):
    goal, error = get_own_goal(request, goal_id)
    if error:
        return error
    form = GoalForm(request.POST, instance=goal)
    if form.is_valid():
        form.save()
        messages.success(request, "Goal updated\nYour changes are saved.")
        return JsonResponse({"id": goal.id})
    return JsonResponse({"errors": form.errors.get_json_data()}, status=400)


@require_POST
def log_progress_ajax(request, goal_id):
    goal, error = get_own_goal(request, goal_id)
    if error:
        return error
    if goal.is_complete:
        return JsonResponse({"message": "This goal is already complete."}, status=400)
    form = ProgressLogForm(request.POST)
    if not form.is_valid():
        return JsonResponse({"errors": form.errors.get_json_data()}, status=400)
    log = form.save(commit=False)
    log.goal = goal
    log.save()
    # The page redraws the card from these numbers and shows the toast, so no reload is needed
    # Texts from the toast frames in Figma ("3 of 5 done. Keep going!")
    done_text = f"{goal.done} of {goal.target} done."
    toast = ("Goal complete", f"{done_text} You did it!") if goal.is_complete else ("Progress saved", f"{done_text} Keep going!")
    return JsonResponse({
        "done": goal.done,
        "target": goal.target,
        "percent": goal.percent,
        "is_complete": goal.is_complete,
        "title": toast[0],
        "message": toast[1],
    })


@require_POST
def delete_goal(request, goal_id):
    goal = get_object_or_404(Goal, pk=goal_id)
    # Only the owner may delete. Visitors who aren't logged in never equal the owner, so they're stopped here too.
    if request.user != goal.user:
        raise PermissionDenied
    goal.delete()
    messages.success(request, "Goal deleted\nIt's off your list now.")
    return redirect("achievements:show_achievements")