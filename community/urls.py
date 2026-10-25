from django.urls import path
from . import views

app_name = "community"

urlpatterns = [
    path("", views.show_questions, name="show_questions"),
    path("show_question/<int:question_id>/", views.show_question_thread, name="show_question_thread"),
    path("questions/add-ajax/", views.create_question_ajax, name="create_question_ajax"),
    path("questions/vote-ajax/<int:question_id>/", views.vote_question_ajax, name="vote_question_ajax"),
    path("show_question/<int:question_id>/answers/add-ajax/", views.create_answer_ajax, name="create_answer_ajax"),
    path("answers/vote-ajax/<int:answer_id>/", views.vote_answer_ajax, name="vote_answer_ajax")
]