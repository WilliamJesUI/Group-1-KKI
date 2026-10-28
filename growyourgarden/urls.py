from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("events/", include("events.urls")),
    path("", include("accounts.urls")),
    path("community/", include("community.urls")),
    path("garden/", include("garden.urls")),
    path("", TemplateView.as_view(template_name="home.html")),
]