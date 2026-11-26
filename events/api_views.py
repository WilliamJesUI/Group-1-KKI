from django.contrib.auth.models import User
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from events.models import Event
from events.serializers import EventSerializer
from events.views import EVENT_FILTERS, filter_events
from growyourgarden.permissions import can_delete
from plants.models import Plant

def events_queryset():
    # Same queries as the website: skip the photo bytes, and load attendees in one go
    return Event.objects.defer("cover_image").select_related("host", "theme_plant").prefetch_related(
        Prefetch("attendees", queryset=User.objects.order_by("pk"))
    )


# GET  /events/api/  anyone can read. Filters like the website: ?filter=upcoming|month|mine&q=seed&plant=tomato
# POST /events/api/  logged-in users host a new event
@api_view(["GET", "HEAD", "POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticatedOrReadOnly])
def event_list(request):
    if request.method in ("GET", "HEAD"):
        selected_filter = request.query_params.get("filter", "upcoming")
        if selected_filter not in dict(EVENT_FILTERS):
            selected_filter = "upcoming"
        events = filter_events(events_queryset(), selected_filter, request.user)
        query = request.query_params.get("q", "").strip()
        if query:
            events = events.filter(Q(name__icontains=query) | Q(theme_plant__name__icontains=query))
        plant_slug = request.query_params.get("plant", "").strip()
        if plant_slug:
            events = events.filter(theme_plant__slug=plant_slug)
        serializer = EventSerializer(events, many=True, context={"request": request})
        return Response(serializer.data)

    serializer = EventSerializer(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    # The host is always the logged-in user, the app can't pick someone else
    serializer.save(host=request.user)
    return Response(serializer.data, status=status.HTTP_201_CREATED)



# GET /events/api/<id>/  anyone. PUT/PATCH only the host. DELETE the host or a moderator.
@api_view(["GET", "HEAD", "PUT", "PATCH", "DELETE"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticatedOrReadOnly])
def event_detail(request, event_id):
    event = get_object_or_404(events_queryset(), pk=event_id)
    if request.method in ("GET", "HEAD"):
        return Response(EventSerializer(event, context={"request": request}).data)

    if request.method == "DELETE":
        if not can_delete(request.user, event.host):
            return Response({"detail": "Only the host can delete this event."}, status=status.HTTP_403_FORBIDDEN)
        event.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    if event.host != request.user:
        return Response({"detail": "Only the host can edit this event."}, status=status.HTTP_403_FORBIDDEN)
    serializer = EventSerializer(
        event, data=request.data, partial=request.method == "PATCH", context={"request": request},
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


# POST /events/api/<id>/rsvp/ with {"going": true} or {"going": false}
@api_view(["POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def event_rsvp(request, event_id):
    event = get_object_or_404(events_queryset(), pk=event_id)
    # Same rules as the RSVP button on the website
    if event.host == request.user:
        return Response({"detail": "You're the host, so you're already going."}, status=status.HTTP_400_BAD_REQUEST)
    if event.status() == "happening":
        return Response({"detail": "RSVPs are closed, this event has already started."}, status=status.HTTP_400_BAD_REQUEST)
    if event.status() == "ended":
        return Response({"detail": "RSVPs are closed, this event has ended."}, status=status.HTTP_400_BAD_REQUEST)

    # The app sends what the user wants instead of "flip it", so a double tap can't undo an RSVP
    if request.data.get("going") is True:
        event.attendees.add(request.user)
    else:
        event.attendees.remove(request.user)
    # Load the event again so going_count and is_going show the new attendees
    event = get_object_or_404(events_queryset(), pk=event_id)
    return Response(EventSerializer(event, context={"request": request}).data)



# GET /events/api/plants/  the theme plant choices for the app's Host an event form
@api_view(["GET"])
def event_plant_choices(request):
    plants = Plant.objects.order_by("name").values("slug", "name")
    return Response(list(plants))