from django.contrib import admin
from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/token/', obtain_auth_token, name='api_token'),
    path('events/', include('events.urls')),
    path('encyclopedia/', include('encyclopedia.urls')),
    path('', include('accounts.urls')),
    path('community/', include('community.urls')),
    path('achievements/', include('achievements.urls')),
    path('garden/', include('garden.urls')),
    path('', include('home.urls')),
]