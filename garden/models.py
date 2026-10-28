import uuid
from django.conf import settings
from django.db import models

class Post(models.Model):
    PLANT_CATEGORIES = [
        ("vegetables", "Vegetables"),
        ("herbs", "Herbs"),
        ("flowers", "Flowers"),
        ("fruits", "Fruits"),
        ("berries", "Berries"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="garden_posts",
    )
    caption = models.TextField(blank=True)
    image_url = models.URLField(blank=True, max_length=500)
    
    # Старое поле для совместимости
    category = models.CharField(
        max_length=20,
        choices=PLANT_CATEGORIES,
        blank=True,
        default="",
    )
    # Новое поле для нескольких категорий (галочки)
    categories = models.JSONField(default=list, blank=True)
    
    plant_tag = models.CharField(max_length=100, blank=True)
    likes = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="liked_posts",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.author.username}: {self.caption[:30]}"

    @property
    def display_categories(self):
        return self.categories or ([self.category] if self.category else [])

class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.author.username}"

class PlantOfTheWeek(models.Model):
    name = models.CharField(max_length=100)
    scientific_name = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    image_url = models.URLField(max_length=500, blank=True)
    badge_text = models.CharField(max_length=50, default="Easy starter", blank=True)

    def __str__(self):
        return self.name