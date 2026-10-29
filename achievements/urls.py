from django.urls import path
from achievements.views import check_in, claim_badge, delete_goal, show_achievements, create_goal_ajax, edit_goal_ajax, log_progress_ajax

app_name = 'achievements'

urlpatterns = [
    path('', show_achievements, name='show_achievements'),
    path('check-in/', check_in, name='check_in'),
    path('goals/create/', create_goal_ajax, name='create_goal'),
    path('goals/<int:goal_id>/edit/', edit_goal_ajax, name='edit_goal'),
    path('goals/<int:goal_id>/log/', log_progress_ajax, name='log_progress'),
    path('goals/<int:goal_id>/delete/', delete_goal, name='delete_goal'),
    path('<slug:slug>/claim/', claim_badge, name='claim_badge'),
]