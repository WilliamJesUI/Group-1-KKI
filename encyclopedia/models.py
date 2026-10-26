from django.conf import settings
from django.db import models
from plants.models import Plant

class SavedPlant(models.Model):
    """A plant bookmarked by a gardener."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_plants")
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name="saved_by")
    saved_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["-saved_at"]
        constraints = [models.UniqueConstraint(fields=["user", "plant"], name="unique_saved_plant_per_user")]
    def __str__(self):
        return f"{self.user} saved {self.plant}"

class PlantCollection(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="plant_collections")
    name = models.CharField(max_length=100, default="My Balcony")
    plants = models.ManyToManyField(Plant, blank=True, related_name="collections")
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ["name"]
    def __str__(self):
        return self.name
