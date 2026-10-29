from django.contrib import admin
from achievements.models import CheckIn, ClaimedBadge, Milestone, UserMetric


@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    list_display = ("title", "metric", "target", "plant_type", "order")
    prepopulated_fields = {"slug": ("title",)}


admin.site.register(UserMetric)
admin.site.register(ClaimedBadge)
admin.site.register(CheckIn)