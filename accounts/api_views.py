from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Profile
from accounts.serializers import (
    DeleteAccountSerializer,
    LoginSerializer,
    ProfileSerializer,
    RegisterSerializer,
)

# The JSON API for accounts, next to the HTML pages in views.py. It uses the same Django session as the website
# (the "sessionid" cookie), so someone logged in on the site is also logged in for the API. For a POST/PATCH/DELETE
# from a logged-in browser, send the CSRF token in the X-CSRFToken header (DRF's SessionAuthentication checks it).


class AccountsAPIView(APIView):
    authentication_classes = [SessionAuthentication]


def own_profile(user):
    # get_or_create also covers users who registered before the accounts app existed, like EditProfileView
    profile, _ = Profile.objects.get_or_create(user=user)
    return profile


class RegisterAPIView(AccountsAPIView):
    """POST /api/register/ makes an account and logs the new user in, like the Register page."""

    permission_classes = [AllowAny]

    def post(self, request):
        if request.user.is_authenticated:
            return Response({"detail": "You are already logged in."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        login(request, user)
        profile = ProfileSerializer(own_profile(user), context={"request": request}).data
        return Response(profile, status=status.HTTP_201_CREATED)


class LoginAPIView(AccountsAPIView):
    """POST /api/login/ with username and password."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        login(request, user)
        profile = ProfileSerializer(own_profile(user), context={"request": request}).data
        return Response(profile)


class LogoutAPIView(AccountsAPIView):
    """POST /api/logout/ ends the session."""

    permission_classes = [AllowAny]

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MyProfileAPIView(AccountsAPIView):
    """
    GET    /api/profile/  my profile
    PATCH  /api/profile/  change some fields (send JSON, or multipart/form-data when uploading a photo)
    PUT    /api/profile/  same as PATCH, but the text fields are required to be complete
    DELETE /api/profile/  delete my account for good (send "password" and "confirm": true)
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request):
        return Response(ProfileSerializer(own_profile(request.user), context={"request": request}).data)

    def _update(self, request, partial):
        profile = own_profile(request.user)
        serializer = ProfileSerializer(profile, data=request.data, partial=partial, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # Read the profile again so the response shows what is really saved
        profile = own_profile(request.user)
        return Response(ProfileSerializer(profile, context={"request": request}).data)

    def patch(self, request):
        return self._update(request, partial=True)

    def put(self, request):
        return self._update(request, partial=False)

    def delete(self, request):
        serializer = DeleteAccountSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = request.user
        # Log out first (this clears the session), then delete. Deleting the User also deletes their Profile,
        # uploaded photos, RSVPs and hosted events (on_delete=CASCADE), same as DeleteAccountView.
        logout(request)
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PublicProfileAPIView(AccountsAPIView):
    """GET /api/profile/<username>/ is public, like the website page. The email is only shown to the owner."""

    permission_classes = [AllowAny]

    def get(self, request, username):
        user = get_object_or_404(User, username=username)
        return Response(ProfileSerializer(own_profile(user), context={"request": request}).data)
