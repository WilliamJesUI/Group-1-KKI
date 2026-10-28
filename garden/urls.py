from django.urls import path
from . import views

app_name = 'garden'

urlpatterns = [
    path('', views.show_garden, name='show_garden'),
    path('create/', views.create_post_ajax, name='create_post_ajax'),
    path('<uuid:post_id>/like/', views.toggle_like_ajax, name='toggle_like_ajax'),
    path('<uuid:post_id>/comment/', views.add_comment_ajax, name='add_comment_ajax'),
    path('<uuid:post_id>/edit/', views.edit_post_ajax, name='edit_post_ajax'),
    path('<uuid:post_id>/delete/', views.delete_post_ajax, name='delete_post_ajax'),
]