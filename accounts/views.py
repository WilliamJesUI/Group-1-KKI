from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.contrib.auth.models import User
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import FormView, TemplateView, UpdateView

from accounts.forms import DeleteAccountForm, EditProfileForm, LoginForm, RegisterForm
from accounts.models import Profile, ProfileImage


class RegisterView(FormView):
    template_name = "accounts/register.html"
    form_class = RegisterForm
    success_url = reverse_lazy("profile:show_profile")

    def dispatch(self, request, *args, **kwargs):
        # Someone who is already logged in has no reason to see the Register page
        if request.user.is_authenticated:
            return redirect("profile:show_profile")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # form.save() makes the User (the post_save signal in models.py then makes the Profile).
        # We log them in straight away, so a new gardener lands on their profile instead of the login page.
        user = form.save()
        login(self.request, user)
        messages.success(self.request, "Welcome to the garden\nYour account is ready. Add a bit about yourself with Edit profile.")
        return redirect(self.get_success_url())


class LoginView(auth_views.LoginView):
    # Django's own LoginView checks the username and password and handles ?next=/some/page/ safely
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        user = form.get_user()
        messages.success(self.request, f"Welcome back\nGood to see you, {user.first_name or user.username}.")
        return response


class LogoutView(auth_views.LogoutView):
    # Since Django 5.0 logging out only works with a POST request (a plain link would be a 405 error),
    # so the navbar uses a small <form method="post"> with a csrf token, see templates/header.html.
    next_page = reverse_lazy("profile:login")

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        # The session is already cleared here. The message travels in a cookie, so the login page can still show it.
        messages.success(request, "Logged out\nSee you in the garden soon.")
        return response


def format_count(number):
    # 1200 becomes "1.2k", 12 stays "12"
    if number >= 1000:
        return f"{number / 1000:.1f}".rstrip("0").rstrip(".") + "k"
    return str(number)


# Sample content copied from the Figma profile page, so the whole page can be checked before the Garden and
# Achievements modules exist. It is shown only while PROFILE_DEMO_DATA = True in settings.py.
# All photos are already credited in docs/CREDITS.md (Garden posts and Plants rows).
DEMO_STATS = (12, 1200, 8, 6)
DEMO_BADGES = [
    {"name": "First sprout", "tone": "bg-brand-soft", "icon": "img/icons/ach-sprout.svg"},
    {"name": "Green thumb", "tone": "bg-pink", "icon": "img/icons/ach-award.svg"},
    {"name": "Event regular", "tone": "bg-lilac", "icon": "img/icons/ach-calendar-lg.svg"},
]
DEMO_SNAPSHOTS = [
    {"image_url": "https://images.pexels.com/photos/6314416/pexels-photo-6314416.jpeg?auto=compress&cs=tinysrgb&w=800", "likes": 128, "caption": "Balcony tomatoes"},
    {"image_url": "https://images.pexels.com/photos/28125162/pexels-photo-28125162.jpeg?auto=compress&cs=tinysrgb&w=800", "likes": 94, "caption": "Sweet basil"},
    {"image_url": "https://images.pexels.com/photos/5685910/pexels-photo-5685910.jpeg?auto=compress&cs=tinysrgb&w=800", "likes": 73, "caption": "Cherry tomatoes on the vine"},
    {"image_url": "https://images.pexels.com/photos/1437424/pexels-photo-1437424.jpeg?auto=compress&cs=tinysrgb&w=800", "likes": 61, "caption": "Rooftop basil"},
]


def demo_data_on():
    return getattr(settings, "PROFILE_DEMO_DATA", False)


def get_profile_stats(user):
    # The four numbers in the stats bar. Garden posts and appreciations come from the Garden app, achievements
    # from the Achievements app. Plants growing is 0 until that module is connected, for example:
    #   plants_growing = UserPlant.objects.filter(user=user).count()
    # (apps are imported here so they don't import each other when Django starts)
    from achievements.models import ClaimedBadge
    from garden.models import Post

    garden_posts = Post.objects.filter(author=user).count()
    # Appreciations = every like on any of this user's posts
    appreciations = Post.likes.through.objects.filter(post__author=user).count()
    # Only badges the user has pressed "Claim badge" for count, same as on the Achievements page
    achievements = ClaimedBadge.objects.filter(user=user, status="APPROVED").count()
    plants_growing = 0
    if demo_data_on():
        garden_posts, appreciations, achievements, plants_growing = DEMO_STATS
    return [
        (format_count(garden_posts), "Garden posts"),
        (format_count(appreciations), "Appreciations"),
        (format_count(achievements), "Achievements"),
        (format_count(plants_growing), "Plants growing"),
    ]


def get_recent_badges(user):
    # The 3 badges this user claimed most recently, for "Recent badges". The template reads badge.name,
    # badge.tone (the background class of the icon square) and badge.icon (a path inside static/),
    # the same things the Achievements page shows for a milestone.
    if demo_data_on():
        return DEMO_BADGES
    from achievements.models import ClaimedBadge

    claims = ClaimedBadge.objects.filter(user=user, status="APPROVED").select_related("milestone").order_by("-claimed_at", "-id")[:3]
    return [
        {"name": claim.milestone.title, "tone": claim.milestone.tone, "icon": claim.milestone.icon}
        for claim in claims
    ]


def get_garden_snapshots(user):
    # The 4 newest garden posts of this user, for the "My garden" grid. The template reads snapshot.image_url
    # (empty for a post without a photo), snapshot.likes and snapshot.caption.
    if demo_data_on():
        return DEMO_SNAPSHOTS
    from garden.models import Post

    posts = (
        Post.objects.filter(author=user)
        .defer("photo")  # we only need the photo's address, not the photo itself
        .annotate(like_count=Count("likes", distinct=True))
        .order_by("-created_at")[:4]
    )
    return [{"image_url": post.photo_src, "likes": post.like_count, "caption": post.caption} for post in posts]


class ProfileView(TemplateView):
    # /profile/<username>/ is public: anyone with the link can look at it, logged in or not (that is what "Share profile"
    # copies). /profile/ means "my profile", so that one needs a login.
    template_name = "accounts/profile.html"

    def dispatch(self, request, *args, **kwargs):
        if "username" not in kwargs and not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        username = self.kwargs.get("username")
        profile_user = get_object_or_404(User, username=username) if username else self.request.user
        # get_or_create also covers users who registered before the accounts app existed and have no Profile yet
        profile, _ = Profile.objects.get_or_create(user=profile_user)
        context.update({
            "profile_user": profile_user,
            "profile": profile,
            "display_name": profile.display_name,
            "is_owner": profile_user == self.request.user,
            "stats": get_profile_stats(profile_user),
            "badges": get_recent_badges(profile_user),
            "snapshots": get_garden_snapshots(profile_user),
        })
        return context


class EditProfileView(LoginRequiredMixin, UpdateView):
    model = Profile
    form_class = EditProfileForm
    template_name = "accounts/edit_profile.html"
    success_url = reverse_lazy("profile:show_profile")

    def get_object(self, queryset=None):
        # Always the logged-in user's own profile, so nobody can edit someone else's by changing the URL
        profile, _ = Profile.objects.get_or_create(user=self.request.user)
        return profile

    def form_valid(self, form):
        messages.success(self.request, "Profile updated\nYour changes are live.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Couldn't save your profile\nPlease check the highlighted fields.")
        return super().form_invalid(form)


class ProfileImageView(View):
    # Serves a photo someone uploaded, from the database. urls.py makes two copies of this view:
    # kind="avatar" for /profile/<username>/picture/ and kind="banner" for /profile/<username>/banner/.
    kind = None

    def get(self, request, username):
        image = get_object_or_404(ProfileImage, profile__user__username=username, kind=self.kind)
        # bytes() because some databases (PostgreSQL) hand back a memoryview
        response = HttpResponse(bytes(image.data), content_type=image.content_type)
        # The link ends in ?v=<number> and the number changes with every new upload, so a day of caching is safe
        response["Cache-Control"] = "public, max-age=86400"
        return response


class DeleteAccountView(LoginRequiredMixin, FormView):
    # Step 1 (GET): a warning page. Step 2 (POST): the right password plus the tick, then the account is deleted.
    template_name = "accounts/delete_account.html"
    form_class = DeleteAccountForm
    success_url = reverse_lazy("profile:login")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        user = self.request.user
        # Log out first (this clears the session), then delete. Deleting the User also deletes their Profile,
        # uploaded photos and RSVPs, and the events they host, because those are linked with on_delete=CASCADE.
        logout(self.request)
        user.delete()
        messages.success(self.request, "Account deleted\nYour account and profile are gone. You're always welcome back in the garden.")
        return super().form_valid(form)
