from django.utils import timezone
from rest_framework import serializers

from events.models import Event
from plants.models import Plant


class EventSerializer(serializers.ModelSerializer):
    # Turns an Event into JSON for the app, and checks the JSON the app sends when it creates or edits one.
    # read_only fields are only sent out. The app can't change them.
    host = serializers.CharField(source="host.username", read_only=True)
    status = serializers.CharField(read_only=True)
    # The app sends the plant's slug (like "tomato"), or null for no theme plant
    theme_plant = serializers.SlugRelatedField(
        slug_field="slug", queryset=Plant.objects.all(), required=False, allow_null=True
    )
    theme_plant_name = serializers.CharField(source="theme_plant.name", read_only=True, default=None)
    cover_url = serializers.SerializerMethodField()
    going_count = serializers.SerializerMethodField()
    is_going = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            "id", "name", "description", "what_to_bring", "location", "start_time", "end_time",
            "theme_plant", "theme_plant_name", "cover_photo_url",
            "host", "status", "cover_url", "going_count", "is_going",
        ]

    def get_cover_url(self, event):
        # A full link (with the domain), because the app is not on the same site as the images
        src = event.cover_src()
        return self.context["request"].build_absolute_uri(src) if src else ""

    def get_going_count(self, event):
        return len(event.attendees.all())

    def get_is_going(self, event):
        user = self.context["request"].user
        return user.is_authenticated and user in event.attendees.all()

    def validate_cover_photo_url(self, url):
        # Same rule as the website form: only https links
        if url and not url.startswith("https://"):
            raise serializers.ValidationError("Please paste a full image link, starting with https://")
        return url

    def validate(self, data):
        # On PATCH only some fields are sent, so fall back to what the event already has
        start_time = data.get("start_time", self.instance.start_time if self.instance else None)
        end_time = data.get("end_time", self.instance.end_time if self.instance else None)
        # No new events in the past (only checked when the start time is sent)
        if "start_time" in data and start_time < timezone.now():
            raise serializers.ValidationError({"start_time": "This date and time has already passed. Please pick a later one."})
        if end_time and start_time and end_time <= start_time:
            raise serializers.ValidationError({"end_time": "The end time has to be after the start time."})
        return data