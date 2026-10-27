import random

from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

# The four colors of the initials avatar in Figma (shown when a user has no profile picture).
# Each profile gets one at random when it is created and keeps it for good, even after a photo is added and removed.
AVATAR_COLORS = [("green", "Green"), ("pink", "Pink"), ("lilac", "Lilac"), ("yellow", "Yellow")]
# Tailwind background classes for those colors, from the theme in templates/base.html
AVATAR_BG_CLASSES = {"green": "bg-brand-soft", "pink": "bg-pink", "lilac": "bg-lilac", "yellow": "bg-butter"}


def initials_for(name):
    # The letters shown on the avatar. One word gives its first letter ("Ala" gives A).
    # Two or more words give the first letters of the first two words ("Ala Tidur" gives AT).
    words = name.split()
    if not words:
        return ""
    if len(words) == 1:
        return words[0][0].upper()
    return (words[0][0] + words[1][0]).upper()


def random_avatar_color():
    # A plain function (not a lambda), because migrations need to be able to refer to it by name
    return random.choice([value for value, label in AVATAR_COLORS])


GROWING_STYLE_CHOICES = [
    ("Balcony garden", "Balcony garden"),
    ("Backyard garden", "Backyard garden"),
    ("Rooftop garden", "Rooftop garden"),
    ("Indoor plants", "Indoor plants"),
    ("Community garden", "Community garden"),
    ("Hydroponics", "Hydroponics"),
]


class Profile(models.Model):
    # Everything about login (username, email, password) stays on Django's built-in User.
    # Profile only adds what the Figma profile page needs. One user has exactly one profile.
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    bio = models.TextField(blank=True, max_length=300)
    location = models.CharField(max_length=100, blank=True)
    # Profile picture and profile banner. Each one holds a link: either an https:// link the user pasted, or, when the
    # user uploaded a photo, the address of our own image page (/profile/<username>/picture/?v=...). That way the
    # templates always just print the value. The uploaded bytes live in ProfileImage below.
    # (cover_image is the banner. The field keeps its first name so no migration is needed to rename it.)
    profile_picture = models.URLField(blank=True, max_length=500)
    cover_image = models.URLField(blank=True, max_length=500)
    # TODO: once the shared Plant model (Encyclopedia) is merged, this can become a ForeignKey to it.
    # README: "select your favorite plant from the API database".
    favorite_plant = models.CharField(max_length=100, blank=True)
    growing_style = models.CharField(max_length=50, blank=True, choices=GROWING_STYLE_CHOICES)
    # Color of the initials avatar. Picked at random once and never changed by the app.
    avatar_color = models.CharField(max_length=10, choices=AVATAR_COLORS, default=random_avatar_color)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile of {self.user.username}"

    @property
    def display_name(self):
        # The "Display name" from Edit profile (kept in the user's first_name, which the navbar already reads),
        # or the username when it is empty
        return self.user.first_name or self.user.username

    @property
    def initials(self):
        return initials_for(self.display_name)

    @property
    def avatar_bg_class(self):
        return AVATAR_BG_CLASSES.get(self.avatar_color, "bg-brand-soft")


class ProfileImage(models.Model):
    # An uploaded photo, stored in the database (like Event.cover_image), because files saved on disk are lost
    # when PWS redeploys. It is a separate table so the photo bytes are not loaded every time we read a Profile,
    # for example in the navbar on every page. One profile has at most one avatar and one banner.
    AVATAR = "avatar"
    BANNER = "banner"
    KIND_CHOICES = [(AVATAR, "Profile picture"), (BANNER, "Profile banner")]

    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="images")
    kind = models.CharField(max_length=10, choices=KIND_CHOICES)
    data = models.BinaryField()
    content_type = models.CharField(max_length=30)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["profile", "kind"], name="one_image_per_kind")]

    def __str__(self):
        return f"{self.get_kind_display()} of {self.profile.user.username}"


@receiver(post_save, sender=User)
def create_profile_for_new_user(sender, instance, created, raw=False, **kwargs):
    # Runs every time a User is saved. "created" is True only the first time, so a Profile is made
    # once when someone registers (or when createsuperuser / the admin adds a user), never again.
    # raw=True means loaddata is loading a fixture, which already contains its own Profile rows.
    if created and not raw:
        Profile.objects.get_or_create(user=instance)

