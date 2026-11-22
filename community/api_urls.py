from django.urls import path
from .api_views import *

app_name = "api"
urlpatterns = [
    path("questions/", question_list, name="question-list"),
]