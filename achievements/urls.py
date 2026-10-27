from django.urls import path
from achievements.views import show_achievements

app_name = 'achievements'

urlpatterns = [
    path('', show_achievements, name='show_achievements'),
]