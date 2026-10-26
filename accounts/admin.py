from django.contrib import admin

from accounts.models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "location", "favorite_plant", "growing_style", "created_at")
    search_fields = ("user__username", "user__email", "location", "favorite_plant")
    list_filter = ("growing_style",)
