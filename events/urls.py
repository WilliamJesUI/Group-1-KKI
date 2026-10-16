from django.urls import path
from events.views import show_events

app_name = 'events'

urlpatterns = [
    path('', show_events, name='show_events'),
]
