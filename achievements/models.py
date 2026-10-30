from django.utils import timezone as dj_timezone
from django.db.models import Sum
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.contrib.auth.models import User
from django.db import models


class Milestone(models.Model):
    # What a milestone counts. Other modules add to these counters with services.record_progress().
    # "checkin_streak" is the exception: it is worked out from the CheckIn table.
    METRIC_CHOICES = [
        ("plants_added", "Plants added"),
        ("harvests_logged", "Harvests logged"),
        ("checkin_streak", "Day check-in streak"),
        ("answers_given", "Answers written"),
        ("host", "Events hosted"),
        ("event_goer", "Events RSVPed"),
        ("plant_collector", "Plants saved"),
    ]
    # Background colour of the icon square. These are the colour names from base.html.
    TONE_CHOICES = [
        ("bg-brand-soft", "Green"),
        ("bg-pink", "Pink"),
        ("bg-lilac", "Lilac"),
        ("bg-[#b8fff8]", "Aqua"),
        ("bg-butter", "Butter"),
    ]

    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=60)
    description = models.CharField(max_length=120)
    metric = models.CharField(max_length=30, choices=METRIC_CHOICES)
    # How many of the metric are needed to finish the milestone
    target = models.PositiveIntegerField()
    # Path inside static/, e.g. img/icons/ach-sprout-lg.svg
    icon = models.CharField(max_length=120)
    tone = models.CharField(max_length=30, choices=TONE_CHOICES, default="bg-brand-soft")
    # Which pill on the page shows this milestone. Empty means it only shows under "All plants".
    plant = models.ForeignKey("plants.Plant", null=True, blank=True, on_delete=models.SET_NULL, related_name="milestones")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


class UserMetric(models.Model):
    # One counter per user and metric, e.g. Rina has answers_given = 7
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="metrics")
    metric = models.CharField(max_length=30)
    value = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "metric"], name="one_metric_per_user")]

    def __str__(self):
        return f"{self.user.username}: {self.metric} = {self.value}"


class ClaimedBadge(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    milestone = models.ForeignKey(Milestone, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    claimed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "milestone")
    def __str__(self):
        return f"{self.user.username} claimed {self.milestone.title}"

class CheckIn(models.Model):
    # One row per user per day. The streak is the number of days in a row ending today (or yesterday).
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="checkins")
    date = models.DateField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "date"], name="one_checkin_per_day")]

    def __str__(self):
        return f"{self.user.username} on {self.date}"

class Goal(models.Model):
    # "Start a goal" form: one goal is about one plant, e.g. "Harvest 5 tomatoes"
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="goals")
    title = models.CharField(max_length=100)
    # Plain text for now. When the Encyclopedia module is merged this becomes a ForeignKey to its Plant model.
    plant = models.ForeignKey("plants.Plant", on_delete=models.PROTECT, related_name="goals")
    # "How many times?" The goal is finished when the logged amounts add up to this number.
    target = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(1000)])
    finish_by = models.DateField(blank=True, null=True)
    # "Why this goal?" a little note to future you
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
 
    class Meta:
        ordering = ["-created_at"]
 
    def __str__(self):
        return self.title
 
    @property
    def done(self):
        # The "3 of 5 done" number: everything logged so far.
        # The goals list adds total_done to each goal in one query, so we use that when it's there.
        annotated = getattr(self, "total_done", None)
        if annotated is not None:
            return annotated
        return self.logs.aggregate(total=Sum("amount"))["total"] or 0
 
    @property
    def percent(self):
        # Rounded down and capped, so a goal never shows more than 100%
        return min(100, self.done * 100 // self.target)
 
    @property
    def is_complete(self):
        return self.done >= self.target
 
 
class ProgressLog(models.Model):
    # "Log progress" form. Deleting a goal deletes its logs too (as the delete dialog says).
    goal = models.ForeignKey(Goal, on_delete=models.CASCADE, related_name="logs")
    # "How many this time?"
    amount = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(1000)])
    date = models.DateField(default=dj_timezone.localdate)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        ordering = ["-date", "-id"]
 
    def __str__(self):
        return f"{self.goal.title}: +{self.amount} on {self.date}"
