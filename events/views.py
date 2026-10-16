from django.shortcuts import render
from django.utils import timezone
from events.models import Event


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
