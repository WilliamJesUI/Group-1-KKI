from django.urls import path
from . import views

app_name = "community"

urlpatterns = [
    path("", views.show_questions, name="show_questions"),
    path("questions/add-ajax/", views.create_question_ajax, name="create_question_ajax")
]