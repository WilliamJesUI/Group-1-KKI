from django.contrib import admin
from garden.models import Comment, PlantOfTheWeek, Post


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("caption", "author", "plant", "created_at")
    list_filter = ("plant__category", "created_at")
    search_fields = ("caption", "plant__name", "author__username")
    # The photo bytes can't be shown or edited as text, so hide them in the form
    exclude = ("photo",)
    raw_id_fields = ("author",)
    autocomplete_fields = ("plant",)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("text", "author", "post", "created_at")
    search_fields = ("text", "author__username")


@admin.register(PlantOfTheWeek)
class PlantOfTheWeekAdmin(admin.ModelAdmin):
    list_display = ("plant", "short_line", "chosen_at")
    autocomplete_fields = ("plant",)
