from django.contrib import admin

from .models import PlantCollection, SavedPlant


@admin.register(PlantCollection)
class PlantCollectionAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "updated_at")
    search_fields = ("name", "user__username")
    list_filter = ("updated_at",)


@admin.register(SavedPlant)
class SavedPlantAdmin(admin.ModelAdmin):
    list_display = ("user", "plant", "saved_at")
    search_fields = ("user__username", "plant__name")
    list_filter = ("saved_at",)
