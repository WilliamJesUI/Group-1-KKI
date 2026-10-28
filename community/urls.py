from django.urls import path
from . import views

app_name = "community"

urlpatterns = [
    path("", views.show_questions, name="show_questions"),
    path("show_question/<int:question_id>/", views.show_question_thread, name="show_question_thread"),
    path("questions/add-ajax/", views.create_question_ajax, name="create_question_ajax"),
    path("questions/update-ajax/<int:question_id>", views.update_question_ajax, name="update_question_ajax"),
    path("questions/delete-ajax/<int:question_id>", views.delete_question_ajax, name="delete_question_ajax"),
    path("questions/vote-ajax/<int:question_id>/", views.vote_question_ajax, name="vote_question_ajax"),
    path("show_question/<int:question_id>/answers/add-ajax/", views.create_answer_ajax, name="create_answer_ajax"),
    path("answers/update-ajax/<int:answer_id>/", views.update_answer_ajax, name="update_answer_ajax"),
    path("answers/delete-ajax/<int:answer_id>/", views.delete_answer_ajax, name = "delete_answer_ajax"),
    path("answers/vote-ajax/<int:answer_id>/", views.vote_answer_ajax, name="vote_answer_ajax"),
    path("popular-plants/", views.popular_plants_ajax, name="popular_plants_ajax"),
]