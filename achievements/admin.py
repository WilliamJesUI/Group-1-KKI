from django.contrib import admin
from achievements.models import CheckIn, ClaimedBadge, Milestone, UserMetric


@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    list_display = ("title", "metric", "target", "plant", "order")
    prepopulated_fields = {"slug": ("title",)}

@admin.register(ClaimedBadge)
class ClaimedBadgeAdmin(admin.ModelAdmin):
    list_display = ("user", "milestone", "status", "claimed_at")
    list_filter = ("status", "claimed_at")
    search_fields = ("user__username", "milestone__title")
    actions = ["approve_claims", "reject_claims"]

    @admin.action(description="Approve selected badge claims")
    def approve_claims(self, request, queryset):
        queryset.update(status="APPROVED")
        self.message_user(request, "Selected badge claims have been approved.")

    @admin.action(description="Reject selected badge claims")
    def reject_claims(self, request, queryset):
        queryset.update(status="REJECTED")
        self.message_user(request, "Selected badge claims have been rejected.")


admin.site.register(UserMetric)
admin.site.register(CheckIn)