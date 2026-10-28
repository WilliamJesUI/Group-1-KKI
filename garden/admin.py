from django.contrib import admin
from .models import Post, Comment, PlantOfTheWeek


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("author", "category", "plant_tag", "created_at")
    list_filter = ("category", "created_at")
    search_fields = ("caption", "plant_tag", "author__username")
    readonly_fields = ("id", "created_at")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("post", "author", "created_at")
    search_fields = ("text", "author__username")
    readonly_fields = ("created_at",)


@admin.register(PlantOfTheWeek)
class PlantOfTheWeekAdmin(admin.ModelAdmin):
    list_display = ("name", "scientific_name", "badge_text")
    search_fields = ("name", "scientific_name")