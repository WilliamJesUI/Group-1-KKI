
from django.utils import timezone

from rest_framework.decorators import api_view
from rest_framework.response import Response

from events.models import Event
from garden.views import (
    GARDEN_FILTERS,
    filter_posts,
    get_plant_of_the_week,
    posts_for,
)
from plants.models import Plant

from garden.api_serializers import (
    GardenPostSerializer,
    GardenPlantSerializer,
    GardenEventSerializer,
)


@api_view(["GET"])
def garden_posts_api(request):
    selected_filter = request.query_params.get(
        "filter", "all"
    )

    if selected_filter not in dict(GARDEN_FILTERS):
        selected_filter = "all"

    posts = filter_posts(
        posts_for(request.user),
        selected_filter,
        request.user,
    )

    plant_slug = request.query_params.get(
        "plant", ""
    ).strip()

    if plant_slug:
        plant = Plant.objects.filter(
            slug=plant_slug
        ).first()

        if plant:
            posts = posts.filter(plant=plant)

    serializer = GardenPostSerializer(
        posts,
        many=True,
        context={"request": request},
    )

    return Response({
        "filter": selected_filter,
        "posts": serializer.data,
    })


@api_view(["GET"])
def garden_overview_api(request):
    plant, short_line = get_plant_of_the_week()

    upcoming_events = Event.objects.filter(
        start_time__gte=timezone.now()
    ).order_by("start_time")[:3]

    plant_data = None

    if plant:
        plant_data = GardenPlantSerializer(
            plant,
            context={"request": request},
        ).data

        plant_data["short_line"] = (
            short_line or plant.description[:160]
        )

    return Response({
        "plant_of_the_week": plant_data,
        "upcoming_events": GardenEventSerializer(
            upcoming_events,
            many=True,
        ).data,
        "garden_tip": (
            "Water the soil, not the leaves. "
            "Early morning is best."
        ),
    })
