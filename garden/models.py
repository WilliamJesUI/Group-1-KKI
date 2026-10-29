import uuid
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from plants.models import Plant


def short_age(moment):
    """How long ago, short like Figma: "just now", "24 min", "2 hr", "3 d", then the date ("7 Nov")."""
    seconds = (timezone.now() - moment).total_seconds()
    if seconds < 60:
        return "just now"
    if seconds < 60 * 60:
        return f"{int(seconds // 60)} min"
    if seconds < 24 * 60 * 60:
        return f"{int(seconds // 3600)} hr"
    if seconds < 7 * 24 * 60 * 60:
        return f"{int(seconds // 86400)} d"
    local = timezone.localtime(moment)
    return f"{local.day} {local:%b}"  # not "%-d", which doesn't work on Windows


class Post(models.Model):
    """One post on the Garden feed: a caption, an optional photo and an optional plant."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="garden_posts")
    caption = models.TextField(max_length=1000)
    # Linked to the shared plant list, so the tag can link to the Encyclopedia and the feed can filter by plant.
    # SET_NULL: if a plant is ever removed, the post stays, just without its tag.
    plant = models.ForeignKey(Plant, on_delete=models.SET_NULL, null=True, blank=True, related_name="garden_posts")
    # The uploaded photo is saved inside the database (not as a file), so it survives PWS redeploys.
    # Same idea as the Events cover photo. photo_type is e.g. "image/png", empty means no photo.
    photo = models.BinaryField(blank=True, null=True)
    photo_type = models.CharField(max_length=20, blank=True)
    # Posts made before uploads existed used a photo link. Kept so they still show their photo.
    image_url = models.URLField(blank=True, max_length=500)
    likes = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="liked_posts", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # Changes every time the post is saved. Used to tell browsers when the photo has changed.
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.author.username}: {self.caption[:30]}"

    @property
    def age_label(self):
        return short_age(self.created_at)

    @property
    def photo_src(self):
        # What to put in <img src="...">: the uploaded photo first, then the old link, otherwise nothing
        if self.photo_type:
            return reverse("garden:show_post_photo", args=[self.id]) + f"?v={int(self.updated_at.timestamp())}"
        return self.image_url


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.author.username}"

    @property
    def age_label(self):
        return short_age(self.created_at)


class PlantOfTheWeek(models.Model):
    """The plant an admin picked for the Garden sidebar (Figma "Set plant of the week").
    Every pick is a new row, and the page shows the newest one. With no pick, the page picks one by week number."""

    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name="weekly_picks")
    # Shown under the plant name. Empty means the page uses the start of the plant's description.
    short_line = models.CharField(max_length=200, blank=True)
    chosen_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-chosen_at"]
        verbose_name_plural = "plants of the week"

    def __str__(self):
        return f"{self.plant.name} ({self.chosen_at:%d %b %Y})"
