from django.urls import path
from garden import views

app_name = "garden"

urlpatterns = [
    path("", views.show_garden, name="show_garden"),
    path("posts/create/", views.create_post, name="create_post"),
    path("posts/<uuid:post_id>/photo/", views.show_post_photo, name="show_post_photo"),
    path("posts/<uuid:post_id>/edit/", views.edit_post, name="edit_post"),
    path("posts/<uuid:post_id>/delete/", views.delete_post, name="delete_post"),
    path("posts/<uuid:post_id>/like/", views.like_post, name="like_post"),
    path("posts/<uuid:post_id>/comments/", views.show_comments, name="show_comments"),
    path("posts/<uuid:post_id>/comments/add/", views.add_comment, name="add_comment"),
    path("comments/<int:comment_id>/delete/", views.delete_comment, name="delete_comment"),
    path("plant-of-the-week/", views.set_plant_of_the_week, name="set_plant_of_the_week"),
]
