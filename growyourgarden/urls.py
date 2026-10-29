"""
URL configuration for grow_a_garden project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('events/', include('events.urls')),
    path('encyclopedia/', include('encyclopedia.urls')),
    path('', include('accounts.urls')),
    path('community/', include('community.urls')),
    # Temporary preview page for base.html, remove once a real home page exists
    path('', TemplateView.as_view(template_name='home.html')),
]
