from django.contrib.auth.models import User
from django.db import models


class Milestone(models.Model):
    # What a milestone counts. Other modules add to these counters with services.record_progress().
    # "checkin_streak" is the exception: it is worked out from the CheckIn table.
    METRIC_CHOICES = [
        ("plants_added", "Plants added"),
        ("harvests_logged", "Harvests logged"),
        ("checkin_streak", "Day check-in streak"),
        ("answers_given", "Questions answered"),
    ]
    # Background colour of the icon square. These are the colour names from base.html.
    TONE_CHOICES = [
        ("bg-brand-soft", "Green"),
        ("bg-pink", "Pink"),
        ("bg-lilac", "Lilac"),
        ("bg-[#b8fff8]", "Aqua"),
        ("bg-butter", "Butter"),
    ]
    PLANT_CHOICES = [("", "All plants"), ("tomato", "Tomato"), ("herbs", "Herbs")]

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
    plant_type = models.CharField(max_length=20, blank=True, choices=PLANT_CHOICES)
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
    # A row exists once the user has pressed "Claim badge" for a finished milestone
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="claimed_badges")
    milestone = models.ForeignKey(Milestone, on_delete=models.CASCADE, related_name="claims")
    claimed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "milestone"], name="one_claim_per_milestone")]

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