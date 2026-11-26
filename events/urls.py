from django.urls import path
from events import api_views
from events.views import show_events, show_event, show_event_cover, create_event_ajax, edit_event_ajax, delete_event, rsvp_event_ajax

app_name = 'events'

urlpatterns = [
    path('', show_events, name='show_events'),
    path('<uuid:event_id>/', show_event, name='show_event'),
    path('<uuid:event_id>/cover/', show_event_cover, name='show_event_cover'),
    path('<uuid:event_id>/edit/', edit_event_ajax, name='edit_event_ajax'),
    path('<uuid:event_id>/delete/', delete_event, name='delete_event'),
    path('<uuid:event_id>/rsvp/', rsvp_event_ajax, name='rsvp_event_ajax'),
    path('host/', create_event_ajax, name='create_event_ajax'),
    path('api/', api_views.event_list, name='api_event_list'),
    path('api/plants/', api_views.event_plant_choices, name='api_event_plants'),
    path('api/<uuid:event_id>/', api_views.event_detail, name='api_event_detail'),
    path('api/<uuid:event_id>/rsvp/', api_views.event_rsvp, name='api_event_rsvp'),
]
