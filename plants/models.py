import json
from functools import cache

from django.conf import settings
from django.db import models
from django.templatetags.static import static

# Our own copies of the plant photos: static/img/plants/<slug>-m.jpg (cards) and <slug>-s.jpg (thumbnails),
# with who took each one in credits.json. Pages load these instead of PlantNet, which often doesn't answer.
PLANT_PHOTO_DIR = settings.BASE_DIR / "static" / "img" / "plants"


@cache  # looks in the folder once per server start, not once per photo
def saved_plant_photos():
    return {path.name for path in PLANT_PHOTO_DIR.glob("*.jpg")}


@cache
def saved_photo_credits():
    """{"sweet-basil": {"credit": "Photo by ..., CC BY-SA 4.0 (Wikimedia Commons)", "url": "..."}, ...}"""
    path = PLANT_PHOTO_DIR / "credits.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


class Plant(models.Model):
    """One plant in our shared plant list. Every module points here with a ForeignKey."""

    class Category(models.TextChoices):
        VEGETABLES = "vegetables", "Vegetables"
        HERBS = "herbs", "Herbs"
        FLOWERS = "flowers", "Flowers"

    class Difficulty(models.TextChoices):
        EASY = "easy", "Easy"
        MEDIUM = "medium", "Medium"
        HARD = "hard", "Hard"

    class Sunlight(models.TextChoices):
        FULL_SUN = "full_sun", "Full sun"
        FULL_SUN_PART_SHADE = "full_sun_part_shade", "Full sun / Part shade"
        PART_SHADE = "part_shade", "Part shade"
        SHADE = "shade", "Shade"

    class Watering(models.TextChoices):
        FREQUENT = "frequent", "Frequent"
        AVERAGE = "average", "Average"
        MINIMUM = "minimum", "Minimum"

    class Cycle(models.TextChoices):
        ANNUAL = "annual", "Annual"
        BIENNIAL = "biennial", "Biennial"
        PERENNIAL = "perennial", "Perennial"

    name = models.CharField(max_length=200)  # shown on the site, like "Sweet basil"
    slug = models.SlugField(max_length=200, unique=True)  # used in links and ?plant= filters
    scientific_name = models.CharField(max_length=200, blank=True)
    family = models.CharField(max_length=100, blank=True)
    category = models.CharField(max_length=20, choices=Category.choices, blank=True)
    difficulty = models.CharField(max_length=10, choices=Difficulty.choices, blank=True)
    sunlight = models.CharField(max_length=30, choices=Sunlight.choices, blank=True)
    watering = models.CharField(max_length=20, choices=Watering.choices, blank=True)
    watering_every = models.CharField(max_length=30, blank=True)  # like "2-3 days"
    cycle = models.CharField(max_length=20, choices=Cycle.choices, blank=True)
    # True when sunlight or watering came from a rule, not from the API
    care_estimated = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    description_url = models.URLField(max_length=500, blank=True)  # Wikipedia text needs a link back
    image_url = models.URLField(max_length=500, blank=True)
    image_credit = models.CharField(max_length=300, blank=True)  # like "Photo by X, CC-BY-SA"
    image_credit_url = models.URLField(max_length=500, blank=True)
    trefle_id = models.IntegerField(unique=True, null=True, blank=True)
    info_source = models.CharField(max_length=200, blank=True)  # like "Trefle, Wikipedia"
        
    @property
    def difficulty_badge_class(self):
        """Background color for the Easy / Medium / Hard tag: green, yellow, pink."""
        return {"easy": "bg-brand-soft", "medium": "bg-butter", "hard": "bg-pink"}.get(self.difficulty, "bg-brand-soft")

    @property
    def category_label(self):
        """One plant's category in singular, like the filter pills and Figma: "Herb", not "Herbs"."""
        return {"vegetables": "Vegetable", "herbs": "Herb", "flowers": "Flower"}.get(self.category, "Plant")

    def photo_url(self, size):
        """The plant's photo in PlantNet size "m" (medium) or "s" (small).
        Our own saved copy if there is one, otherwise the PlantNet link (PlantNet /o/ is the huge original)."""
        if not self.image_url:
            return ""
        name = f"{self.slug}-{size}.jpg"
        if name in saved_plant_photos():
            return static(f"img/plants/{name}")
        return self.image_url.replace("/image/o/", f"/image/{size}/")

    @property
    def photo_credit(self):
        """Who took the photo the site shows: the saved copy's credit, or the original PlantNet one."""
        saved = saved_photo_credits().get(self.slug)
        return saved["credit"] if saved and self.card_image_url.startswith("/static/") else self.image_credit

    @property
    def photo_credit_url(self):
        saved = saved_photo_credits().get(self.slug)
        return saved["url"] if saved and self.card_image_url.startswith("/static/") else self.image_credit_url

    @property
    def card_image_url(self):
        """Medium-size photo for cards."""
        return self.photo_url("m")

    @property
    def thumb_image_url(self):
        """Small photo for little round thumbnails (like Community's Popular Plants), a few KB instead of a few MB."""
        return self.photo_url("s")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name