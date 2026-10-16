from django.urls import path
from events.views import show_events, show_event, show_event_cover, create_event_ajax, edit_event_ajax

app_name = 'events'

urlpatterns = [
    path('', show_events, name='show_events'),
    path('<uuid:event_id>/', show_event, name='show_event'),
    path('<uuid:event_id>/cover/', show_event_cover, name='show_event_cover'),
    path('<uuid:event_id>/edit/', edit_event_ajax, name='edit_event_ajax'),
    path('host/', create_event_ajax, name='create_event_ajax'),
]
