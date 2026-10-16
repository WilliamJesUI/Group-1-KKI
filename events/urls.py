from django.urls import path
from events.views import show_events, show_event, create_event_ajax

app_name = 'events'

urlpatterns = [
    path('', show_events, name='show_events'),
    path('<uuid:event_id>/', show_event, name='show_event'),
    path('host/', create_event_ajax, name='create_event_ajax'),
]
