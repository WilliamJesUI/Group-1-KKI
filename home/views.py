from datetime import timedelta

from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.urls import reverse
from django.utils import timezone

from home import services
from home.services import SHELF_PILLS, safely


# ensure_csrf_cookie: the like, comment and RSVP buttons on the landing page send POSTs with fetch
@ensure_csrf_cookie
def show_landing(request):
    """The landing page at "/" (Figma "Landing / guest" and "Landing / logged in"). Guests can look at
    everything here, every button that changes something sends them to Log in first."""
    category = request.GET.get("shelf", "all")
    if category not in dict(SHELF_PILLS):
        category = "all"
    week = safely(services.plant_of_the_week, {"plant": None, "short_line": ""})
    shelf_context = {
        "shelf": safely(lambda: services.plant_shelf(category, week["plant"]), []),
        "shelf_pills": SHELF_PILLS,
        "category": category,
    }
    # ?partial=1 comes from landing.js when a pill above the plant shelf is clicked: send only the shelf
    if request.GET.get("partial") == "1":
        return render(request, "home/plant_shelf.html", shelf_context)

    top_post, more_posts = safely(lambda: services.garden_posts(request.user), (None, []))
    today = timezone.localdate()
    numbers = safely(services.site_numbers, None)
    events = safely(lambda: services.upcoming_events(request.user), [])
    context = {
        **shelf_context,
        "week": week,
        "issue": today.isocalendar().week,
        "week_start": today - timedelta(days=today.weekday()),
        "numbers": numbers,
        "numbers_list": services.numbers_list(numbers),
        "garden_url": reverse("garden:show_garden"),
        "shelf_title": f"{numbers['plants']} plants," if numbers else "Every plant,",
        "plants_label": f"See all {numbers['plants']} plants" if numbers else "See all plants",
        "events_label": f"All {numbers['events']} upcoming events" if numbers else "All upcoming events",
        "posters": safely(services.posters_this_week, 0),
        "top_post": top_post,
        "more_posts": more_posts,
        "events": events,
        "questions": safely(services.newest_questions, []),
        "badges": safely(services.badges, {"top": [], "latest": None}),
    }
    if request.user.is_authenticated:
        context["mine"] = safely(lambda: services.your_week(request.user), None)
    context["contents"] = services.contents(numbers, events[0] if events else None, context.get("mine"))
    return render(request, "home/landing.html", context)
