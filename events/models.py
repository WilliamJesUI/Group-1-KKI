import uuid
from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse


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
    # An uploaded cover photo is saved inside the database (not as a file), so it survives PWS redeploys.
    # cover_image holds the image bytes, cover_image_type holds e.g. "image/png" (empty means no upload).
    cover_image = models.BinaryField(blank=True, null=True)
    cover_image_type = models.CharField(max_length=20, blank=True)
    # One host per event, one user can host many events
    host = models.ForeignKey(User, on_delete=models.CASCADE, related_name="hosted_events")
    # One event can have many attendees, and one user can RSVP to many events
    attendees = models.ManyToManyField(User, related_name="rsvped_events", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # Changes every time the event is saved. Used to tell browsers when the cover photo has changed.
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_time"]

    def __str__(self):
        return self.name

    def cover_src(self):
        # What to put in <img src="...">: the uploaded photo first, then the link, otherwise nothing
        if self.cover_image_type:
            # ?v=... changes whenever the event is saved, so browsers download the new photo instead of an old saved copy
            version = int(self.updated_at.timestamp())
            return reverse("events:show_event_cover", args=[self.id]) + f"?v={version}"
        return self.cover_photo_url
