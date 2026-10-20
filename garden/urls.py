from django.urls import path
from . import views

app_name = 'garden'

urlpatterns = [
    path('', views.show_garden, name='show_garden'),
    path('create/', views.create_post_ajax, name='create_post_ajax'),
    path('<uuid:post_id>/like/', views.toggle_like_ajax, name='toggle_like_ajax'),
]