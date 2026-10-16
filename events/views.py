from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from events.forms import EventForm
from events.models import Event


def get_initials(user):
    # "Rina Wulandari" becomes "RW". Users without a name get the first two letters of their username.
    if user.first_name:
        return (user.first_name[:1] + user.last_name[:1]).upper()
    return user.username[:2].upper()


def get_when_label(start_time):
    # "Today", "Tomorrow" or "This Saturday" for events in the next week, otherwise nothing
    days_away = (timezone.localtime(start_time).date() - timezone.localdate()).days
    if days_away == 0:
        return "Today"
    if days_away == 1:
        return "Tomorrow"
    if days_away < 7:
        return "This " + timezone.localtime(start_time).strftime("%A")
    return ""


def show_events(request):
    # The soonest event that hasn't started yet, for the "Next up" card
    # defer("cover_image") skips loading the photo bytes, the page only needs the cover URL
    events = Event.objects.defer("cover_image")
    next_event = events.filter(start_time__gte=timezone.now()).first()
    context = {
        "event_list": events,
        "next_event": next_event,
        "next_event_when": get_when_label(next_event.start_time) if next_event else "",
        # An empty form for the "Host an event" pop-up
        "form": EventForm(),
    }
    return render(request, "event_list.html", context)


def show_event(request, event_id):
    event = get_object_or_404(Event.objects.defer("cover_image"), pk=event_id)
    going_count = event.attendees.count()
    context = {
        "event": event,
        "going_count": going_count,
        # Only the first 4 attendees get an avatar, the rest are shown as "+N"
        "attendee_initials": [get_initials(user) for user in event.attendees.all()[:4]],
        "more_going": going_count - 4,
        "host_initials": get_initials(event.host),
        "host_event_count": event.host.hosted_events.count(),
        # Split the text box into a list, skipping empty lines
        "bring_list": [line.strip() for line in event.what_to_bring.splitlines() if line.strip()],
        "is_host": request.user == event.host,
    }
    return render(request, "event_detail.html", context)


def show_event_cover(request, event_id):
    # Sends the uploaded cover photo from the database to the browser, like a normal image file
    event = get_object_or_404(Event, pk=event_id)
    if not event.cover_image_type:
        raise Http404("This event has no uploaded cover photo.")
    response = HttpResponse(bytes(event.cover_image), content_type=event.cover_image_type)
    # Let the browser keep the photo for an hour instead of downloading it on every visit
    response["Cache-Control"] = "public, max-age=3600"
    return response


@require_POST
def create_event_ajax(request):
    # Not @login_required: for fetch requests we want a JSON error, not a redirect to a login page
    if not request.user.is_authenticated:
        return JsonResponse({"message": "Please log in to host an event."}, status=403)

    form = EventForm(request.POST)
    if form.is_valid():
        event = form.save(commit=False)
        event.start_time = form.cleaned_data["start_time"]
        event.end_time = form.cleaned_data["end_time"]
        event.host = request.user
        event.save()
        return JsonResponse(
            {"message": "Event published.", "url": reverse("events:show_event", args=[event.id])},
            status=201,
        )
    return JsonResponse({"errors": form.errors.get_json_data()}, status=400)
