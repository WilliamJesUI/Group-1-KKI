from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('events/', include('events.urls')),
    path('encyclopedia/', include('encyclopedia.urls')),
    path('', include('accounts.urls')),
    path('community/', include('community.urls')),
    path('achievements/', include('achievements.urls')),
    path('garden/', include('garden.urls')),
    # Temporary preview page for base.html, remove once a real home page exists
    path('', TemplateView.as_view(template_name='home.html')),
]