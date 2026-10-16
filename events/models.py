import uuid
from django.contrib.auth.models import User
from django.db import models


class Event(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField()
    # One item per line, shown as a checklist on the event page
    what_to_bring = models.TextField(blank=True)
    location = models.CharField(max_length=255)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(blank=True, null=True)
    cover_photo_url = models.URLField(blank=True, max_length=500)
    # One host per event, one user can host many events
    host = models.ForeignKey(User, on_delete=models.CASCADE, related_name="hosted_events")
    # One event can have many attendees, and one user can RSVP to many events
    attendees = models.ManyToManyField(User, related_name="rsvped_events", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["start_time"]

    def __str__(self):
        return self.name
