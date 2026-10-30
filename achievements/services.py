from datetime import timedelta

from django.db.models import F, Q, Sum
from django.utils import timezone

from achievements.models import CheckIn, ClaimedBadge, Milestone, ProgressLog, UserMetric


def get_stored_metric(user, metric):
    """Return a saved counter, including when no counter row exists yet."""
    counter = UserMetric.objects.filter(user=user, metric=metric).first()
    return counter.value if counter else 0


def plants_in_garden(user):
    """Different plants this user saved in the Encyclopedia (any collection, or the old saved list)."""
    from plants.models import Plant  # imported here so the apps don't import each other at start-up

    return Plant.objects.filter(Q(collections__user=user) | Q(saved_by__user=user)).distinct().count()


def harvests_logged(user):
    """Everything logged with "Log progress" on the user's goals counts as a harvest."""
    return ProgressLog.objects.filter(goal__user=user).aggregate(total=Sum("amount"))["total"] or 0


# How each milestone metric is counted from the other modules. The keys are Milestone.METRIC_CHOICES,
# plus a few older names that milestones made in /admin/ may still use.
BADGE_RULES = {
    "plants_added": plants_in_garden,
    "plant_collector": plants_in_garden,
    "plants_saved": plants_in_garden,
    "harvests_logged": harvests_logged,
    "host": lambda user: user.hosted_events.count(),
    "events_hosted": lambda user: user.hosted_events.count(),
    "event_goer": lambda user: user.rsvped_events.count(),
    "events_rsvped": lambda user: user.rsvped_events.count(),
    "posts_shared": lambda user: user.garden_posts.count(),
    "answers_given": lambda user: user.answers.count(),
}

def record_progress(user, metric, amount=1):
    """Add to a user's counter. Other modules call this, e.g. record_progress(request.user, "answers_given")."""
    counter, _ = UserMetric.objects.get_or_create(user=user, metric=metric)
    UserMetric.objects.filter(pk=counter.pk).update(value=F("value") + amount)


def get_metric(user, metric):
    # Visitors who are not logged in have no progress
    if not user.is_authenticated:
        return 0
    rule = BADGE_RULES.get(metric)
    if rule is not None:
        # Real data from the other modules, plus anything added with record_progress()
        try:
            return rule(user) + get_stored_metric(user, metric)
        except Exception:
            return get_stored_metric(user, metric)
    # The streak comes from check-ins, every other metric is a stored counter
    if metric == "checkin_streak":
        return current_streak(user)
    counter = UserMetric.objects.filter(user=user, metric=metric).first()
    return counter.value if counter else 0


def check_in_today(user):
    """Returns True if this is the first check-in today, False if the user already checked in."""
    _, created = CheckIn.objects.get_or_create(user=user, date=timezone.localdate())
    return created


def current_streak(user):
    # Count back day by day from today. A streak still counts if the user hasn't checked in yet today.
    days = set(CheckIn.objects.filter(user=user).values_list("date", flat=True))
    day = timezone.localdate()
    if day not in days:
        day -= timedelta(days=1)
    streak = 0
    while day in days:
        streak += 1
        day -= timedelta(days=1)
    return streak


def build_milestones(user):
    """One entry per milestone: percent done, and whether it is ready to claim or already claimed."""
    claims_map = {}
    if user.is_authenticated:
        claims = ClaimedBadge.objects.filter(user=user).values("milestone_id", "status")
        claims_map = {claim["milestone_id"]: claim["status"] for claim in claims}
    cards = []
    for milestone in Milestone.objects.select_related("plant"):
        progress = min(get_metric(user, milestone.metric), milestone.target)
        claim_status = claims_map.get(milestone.id)
        
        is_approved = claim_status == "APPROVED"
        is_pending = claim_status == "PENDING"
        cards.append({
            "milestone": milestone,
            # Whole numbers rounded down, so 99.6% never shows as 100% before it can be claimed
            "percent": progress * 100 // milestone.target,
            "claimed": is_approved,
            "pending": is_pending,
            "status": claim_status,
            "ready": progress >= milestone.target and not (is_approved or is_pending),
        })
    return cards


def can_claim(user, milestone):
    if not user.is_authenticated:
        return False
    already_claimed = ClaimedBadge.objects.filter(
        user=user, 
        milestone=milestone, 
        status__in=['PENDING', 'APPROVED']
    ).exists()
    
    if already_claimed:
        return False
    progress = get_metric(user, milestone.metric)
    return progress >= milestone.target
