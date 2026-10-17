from django.http import Http404, HttpResponse, JsonResponse
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
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


# ensure_csrf_cookie: the RSVP button uses fetch, which needs the csrftoken cookie even on pages without a form
@ensure_csrf_cookie
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
        # Whether the logged-in user already RSVP'd, so the button starts as "Going"
        "is_going": request.user.is_authenticated and event.attendees.filter(pk=request.user.pk).exists(),
    }
    if context["is_host"]:
        # The edit pop-up, already filled in with this event's details
        context["form"] = EventForm(instance=event)
    return render(request, "event_detail.html", context)


def show_event_cover(request, event_id):
    # Sends the uploaded cover photo from the database to the browser, like a normal image file
    event = get_object_or_404(Event, pk=event_id)
    if not event.cover_image_type:
        raise Http404("This event has no uploaded cover photo.")
    response = HttpResponse(bytes(event.cover_image), content_type=event.cover_image_type)
    # Let the browser keep the photo for a day. When the event changes, the ?v= part of the URL changes too,
    # so the browser treats it as a new photo and downloads it again.
    response["Cache-Control"] = "public, max-age=86400"
    return response


def save_event_from_form(event, form):
    # Used by both create and edit: saves the parts the form can't save by itself (times and photo)
    event.start_time = form.cleaned_data["start_time"]
    event.end_time = form.cleaned_data["end_time"]
    cover = form.cleaned_data["cover_upload"]
    if cover:
        event.cover_image = cover["data"]
        event.cover_image_type = cover["type"]
    elif form.cleaned_data["remove_cover"]:
        event.cover_image = None
        event.cover_image_type = ""
    event.save()


@require_POST
def create_event_ajax(request):
    # Not @login_required: for fetch requests we want a JSON error, not a redirect to a login page
    if not request.user.is_authenticated:
        return JsonResponse({"message": "Please log in to host an event."}, status=403)

    # request.FILES holds the uploaded photo, request.POST holds everything else
    form = EventForm(request.POST, request.FILES)
    if form.is_valid():
        event = form.save(commit=False)
        event.host = request.user
        save_event_from_form(event, form)
        return JsonResponse(
            {"message": "Event published.", "url": reverse("events:show_event", args=[event.id])},
            status=201,
        )
    return JsonResponse({"errors": form.errors.get_json_data()}, status=400)


@require_POST
def edit_event_ajax(request, event_id):
    if not request.user.is_authenticated:
        return JsonResponse({"message": "Please log in to edit this event."}, status=403)
    event = get_object_or_404(Event, pk=event_id)
    # Hiding the Edit button isn't enough, anyone could send this request with fetch, so check the host here too
    if event.host != request.user:
        return JsonResponse({"message": "Only the host can edit this event."}, status=403)

    # instance=event means "update this event" instead of making a new one
    form = EventForm(request.POST, request.FILES, instance=event)
    if form.is_valid():
        event = form.save(commit=False)
        save_event_from_form(event, form)
        return JsonResponse({"message": "Event updated.", "url": reverse("events:show_event", args=[event.id])})
    return JsonResponse({"errors": form.errors.get_json_data()}, status=400)



@require_POST
def rsvp_event_ajax(request, event_id):
    # Not @login_required: fetch needs a JSON error it can read, not a redirect
    if not request.user.is_authenticated:
        return JsonResponse({"message": "Please log in to RSVP."}, status=403)
    event = get_object_or_404(Event.objects.defer("cover_image"), pk=event_id)

    # The button is hidden for these cases, but anyone could still send the request, so check here too
    if event.host == request.user:
        return JsonResponse({"message": "You're the host, so you're already going."}, status=400)
    if event.status() == "happening":
        return JsonResponse({"message": "RSVPs are closed, this event has already started."}, status=400)
    if event.status() == "ended":
        return JsonResponse({"message": "RSVPs are closed, this event has ended."}, status=400)

    # The button sends what the user wants (going=true or going=false) instead of "flip it",
    # so clicking in two open tabs can't accidentally undo an RSVP
    if request.POST.get("going") == "true":
        event.attendees.add(request.user)
    else:
        event.attendees.remove(request.user)

    going_count = event.attendees.count()
    return JsonResponse({
        "going": event.attendees.filter(pk=request.user.pk).exists(),
        "going_count": going_count,
        # For redrawing the avatar row on the event page
        "attendee_initials": [get_initials(user) for user in event.attendees.all()[:4]],
        "more_going": max(going_count - 4, 0),
    })

@require_POST
def delete_event(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    # Only the host may delete. Visitors who aren't logged in never equal the host, so they're stopped here too.
    if request.user != event.host:
        raise PermissionDenied
    event.delete()
    return redirect("events:show_events")
