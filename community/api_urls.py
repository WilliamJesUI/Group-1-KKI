from django.urls import path
from community import api_views

app_name = "api"
urlpatterns = [
    path("questions/", api_views.question_list, name="question-list"),
    path("questions/<int:question_id>/", api_views.question_detail, name="question-detail"),
    path("questions/<int:question_id>/answers", api_views.answers_for_question, name="answers-for-question"),
    path("answers/<int:answer_id>/", api_views.answer_detail, name="answer-detail"),
]