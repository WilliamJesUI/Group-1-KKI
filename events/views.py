from django.shortcuts import render
from events.models import Event


def show_events(request):
    context = {
        "event_list": Event.objects.all(),
    }
    return render(request, "event_list.html", context)
