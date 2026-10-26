from django.db import models


class Plant(models.Model):
    class Category(models.TextChoices):
        VEGETABLES = "vegetables", "Vegetables"
        HERBS = "herbs", "Herbs"
        FLOWERS = "flowers", "Flowers"

    name = models.CharField(max_length=200)  # shown on the site, like "Sweet basil"
    slug = models.SlugField(max_length=200, unique=True)  # used in links and ?plant= filters
    scientific_name = models.CharField(max_length=200, blank=True)
    category = models.CharField(max_length=20, choices=Category.choices, blank=True)
    description = models.TextField(blank=True)
    image_url = models.URLField(max_length=500, blank=True)
    image_credit = models.CharField(max_length=300, blank=True)
    trefle_id = models.IntegerField(unique=True, null=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name