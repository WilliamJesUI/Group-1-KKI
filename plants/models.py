from django.db import models


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
    def card_image_url(self):
        """Medium-size photo for cards. PlantNet /o/ is the full original, which is slow to load."""
        return self.image_url.replace("/image/o/", "/image/m/")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name