from django.contrib import admin
from .models import Post, Comment, PlantOfTheWeek


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("caption", "author", "created_at")
    list_filter = ("created_at",)
    search_fields = ("caption", "plant_tag", "author__username")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("text", "author", "post", "created_at")
    search_fields = ("text", "author__username")


@admin.register(PlantOfTheWeek)
class PlantOfTheWeekAdmin(admin.ModelAdmin):
    list_display = ("name", "scientific_name")