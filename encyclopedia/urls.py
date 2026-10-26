from django.urls import path
from . import views

app_name = "encyclopedia"
urlpatterns = [
    path("", views.encyclopedia, name="index"),
    path("collection/", views.my_collection, name="collection"),
    path("collection/<slug:slug>/remove/", views.remove_from_collection, name="remove_from_collection"),
    path("<slug:slug>/save/", views.toggle_saved, name="toggle_saved"),
    path("<slug:slug>/", views.plant_detail, name="detail"),
]
