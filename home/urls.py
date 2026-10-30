from django.urls import path

from home import views

app_name = "home"

urlpatterns = [
    path("", views.show_landing, name="show_landing"),
]
