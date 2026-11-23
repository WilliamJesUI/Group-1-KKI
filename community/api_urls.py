from django.urls import path
from community import api_views

app_name = "api"
urlpatterns = [
    path("questions/", api_views.question_list, name="question-list"),
    path("questions/<int:question_id>/", api_views.answers_for_question, name="answers-for-question"),
]