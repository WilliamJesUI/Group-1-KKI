from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from plants.models import Plant
from achievements.forms import GoalForm, ProgressLogForm
from achievements.models import ClaimedBadge, Goal, Milestone
from achievements.services import build_milestones, can_claim, check_in_today, get_metric



@ensure_csrf_cookie
def show_achievements(request):
    user = request.user
    selected_plant_slug = request.GET.get("plant", "")

    cards = build_milestones(user)

    total = len(cards)
    unlocked = sum(1 for card in cards if card["claimed"])
    in_progress = sum(
        1 for card in cards
        if not card["claimed"] and card["percent"] > 0
    )

    plant_objects = (
        Plant.objects
        .filter(milestones__isnull=False)
        .distinct()
        .order_by("name")
    )

    plant_filters = [
        (plant.slug, plant.name)
        for plant in plant_objects
    ]

    available_plant_slugs = {slug for slug, _ in plant_filters}
    if selected_plant_slug not in available_plant_slugs:
        selected_plant_slug = ""

    shown = [
        card for card in cards
        if not selected_plant_slug or card["milestone"].plant_id and
        card["milestone"].plant.slug == selected_plant_slug
    ]

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
        "plant_filters": plant_filters,
        "selected_plant": selected_plant_slug,
        "goals": (
            list(
                Goal.objects.filter(user=user).annotate(
                    total_done=Coalesce(Sum("logs__amount"), 0)
                )
            )
            if user.is_authenticated else []
        ),
        "goal_form": GoalForm(),
        "log_form": ProgressLogForm(),
    }

    return render(request, "achievements.html", context)
@require_POST
def claim_badge(request, slug):
    milestone = get_object_or_404(Milestone, slug=slug)
    if not request.user.is_authenticated:
        messages.error(request, "Log in first\nYou need an account to claim badges.")
        return redirect("achievements:show_achievements")

    existing = ClaimedBadge.objects.filter(user=request.user, milestone=milestone).first()
    if existing and existing.status == "PENDING":
        messages.info(request, f"Pending\nYour claim for {milestone.title} is waiting for admin approval.")
    elif existing and existing.status == "REJECTED":
        messages.error(request, f"Claim rejected\nYour claim for {milestone.title} was not approved.")
    elif existing:
        messages.info(request, f"Already unlocked\nYou already have {milestone.title}.")
    elif not can_claim(request.user, milestone):
        messages.error(request, "Not ready yet\nFinish the milestone first.")
    else:
        ClaimedBadge.objects.create(user=request.user, milestone=milestone)
        messages.success(request, f"Claim submitted!\nWaiting for admin approval to unlock {milestone.title}.")
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
        goal = form.save()
        return JsonResponse({
            'status': 'success',
            'message': "Goal updated\nYour changes are saved.",
            'goal': serialize_goal(goal)
        })
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

def serialize_goal(goal):
    return {
        'id': goal.id,
        'title': goal.title,
        'plant_id': goal.plant_id,
        'plant_name': str(goal.plant),
        'target': goal.target,
        'done': goal.done,
        'percent': goal.percent,
        'is_complete': goal.is_complete,
        'finish_by': goal.finish_by.strftime('%Y-%m-%d') if goal.finish_by else '',
        'finish_by_formatted': goal.finish_by.strftime('%a, %d %b %Y') if goal.finish_by else '',
        'reason': goal.reason or ''
    }
@require_POST
def delete_goal(request, goal_id):
    goal, err_response = get_own_goal(request, goal_id)
    if err_response:
        return err_response
    goal.delete()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
        return JsonResponse({
            'status': 'success',
            'message': "Goal deleted\nIt's off your list now.",
            'goal_id': goal_id
        })
    messages.success(request, "Goal deleted\nIt's off your list now.")
    return redirect("achievements:show_achievements")
