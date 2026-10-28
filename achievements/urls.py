from django.urls import path
from achievements.views import check_in, claim_badge, show_achievements

app_name = 'achievements'

urlpatterns = [
    path('', show_achievements, name='show_achievements'),
    path('check-in/', check_in, name='check_in'),
    path('<slug:slug>/claim/', claim_badge, name='claim_badge'),
]