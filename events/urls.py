from django.urls import path
from events.views import show_events, show_event

app_name = 'events'

urlpatterns = [
    path('', show_events, name='show_events'),
    path('<uuid:event_id>/', show_event, name='show_event'),
]
