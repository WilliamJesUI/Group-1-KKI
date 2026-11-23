from django.urls import path

from accounts.api_views import (
    LoginAPIView,
    LogoutAPIView,
    MyProfileAPIView,
    PublicProfileAPIView,
    RegisterAPIView,
)
from accounts.views import DeleteAccountView, EditProfileView, LoginView, LogoutView, ProfileImageView, ProfileView, RegisterView

# app_name is "profile" (not "accounts") on purpose: the navbar in templates/header.html lights up the Profile tab
# when app_name is "profile", see docs/TEAM-GUIDE.md section 2.
app_name = 'profile'

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', ProfileView.as_view(), name='show_profile'),
    # "edit/" and "delete/" have to stay above "<str:username>/", otherwise they would be read as usernames
    path('profile/edit/', EditProfileView.as_view(), name='edit_profile'),
    path('profile/delete/', DeleteAccountView.as_view(), name='delete_account'),
    path('profile/<str:username>/', ProfileView.as_view(), name='show_user_profile'),
    # Uploaded photos (see ProfileImageView)
    path('profile/<str:username>/picture/', ProfileImageView.as_view(kind='avatar'), name='picture'),
    path('profile/<str:username>/banner/', ProfileImageView.as_view(kind='banner'), name='banner'),

    # JSON API (Django REST Framework), see accounts/api_views.py
    path('api/register/', RegisterAPIView.as_view(), name='api_register'),
    path('api/login/', LoginAPIView.as_view(), name='api_login'),
    path('api/logout/', LogoutAPIView.as_view(), name='api_logout'),
    path('api/profile/', MyProfileAPIView.as_view(), name='api_my_profile'),
    path('api/profile/<str:username>/', PublicProfileAPIView.as_view(), name='api_profile'),
]
