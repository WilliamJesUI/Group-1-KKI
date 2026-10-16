from django.shortcuts import get_object_or_404, render
from django.utils import timezone
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
    next_event = Event.objects.filter(start_time__gte=timezone.now()).first()
    context = {
        "event_list": Event.objects.all(),
        "next_event": next_event,
        "next_event_when": get_when_label(next_event.start_time) if next_event else "",
    }
    return render(request, "event_list.html", context)


def show_event(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
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
