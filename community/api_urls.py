from django.urls import path
from .api_views import *

app_name = "api"
urlpatterns = [
    path("questions/", question_list, name="question-list"),
    path("questions/<int:question_id>/", answer_list, name="answer-list"),
    path("answers/<int:answer_id>/", answer_detail, name="answer-detail"),
]