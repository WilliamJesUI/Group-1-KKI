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