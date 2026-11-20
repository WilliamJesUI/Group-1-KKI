import uuid
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from plants.models import Plant


# Converts a timestamp into a short, human-readable age label.
def short_age(moment):
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
    return f"{local.day} {local:%b}"


class Post(models.Model):
    """One post on the Garden feed."""

    # UUID provides a unique identifier for every post.
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Each post belongs to one user.
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="garden_posts"
    )

    caption = models.TextField(max_length=1000)

    # A post can optionally be connected to a plant.
    plant = models.ForeignKey(
        Plant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="garden_posts"
    )

    # Uploaded image data is stored in the database.
    photo = models.BinaryField(blank=True, null=True)
    photo_type = models.CharField(max_length=20, blank=True)

    # Keeps compatibility with older posts that used image URLs.
    image_url = models.URLField(blank=True, max_length=500)

    # Many users can like many posts.
    likes = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="liked_posts",
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Newest posts appear first.
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.author.username}: {self.caption[:30]}"

    @property
    def age_label(self):
        # Returns a readable time label for the template.
        return short_age(self.created_at)

    @property
    def photo_src(self):
        # Returns the uploaded photo URL or the legacy image URL.
        if self.photo_type:
            return (
                reverse("garden:show_post_photo", args=[self.id])
                + f"?v={int(self.updated_at.timestamp())}"
            )
        return self.image_url


class Comment(models.Model):
    # Every comment belongs to one post.
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="comments"
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    text = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Comments are displayed from oldest to newest.
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.author.username}"

    @property
    def age_label(self):
        return short_age(self.created_at)


class PlantOfTheWeek(models.Model):
    """Stores the plant selected for the Garden sidebar."""

    plant = models.ForeignKey(
        Plant,
        on_delete=models.CASCADE,
        related_name="weekly_picks"
    )

    short_line = models.CharField(max_length=200, blank=True)
    chosen_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # The most recently selected plant appears first.
        ordering = ["-chosen_at"]
        verbose_name_plural = "plants of the week"

    def __str__(self):
        return f"{self.plant.name} ({self.chosen_at:%d %b %Y})"