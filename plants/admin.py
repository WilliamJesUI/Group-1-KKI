from django.contrib import admin

from .models import Plant


@admin.register(Plant)
class PlantAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "scientific_name"]
    list_filter = ["category"]
    search_fields = ["name", "scientific_name"]
    prepopulated_fields = {"slug": ["name"]}