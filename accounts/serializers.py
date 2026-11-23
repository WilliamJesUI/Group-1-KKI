import time

from django.contrib.auth import authenticate, password_validation
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError as DjangoValidationError
from django.urls import reverse
from rest_framework import serializers

from accounts.forms import (
    IMAGE_LINK_ERROR,
    IMAGE_SLOTS,
    MAX_IMAGE_SIZE,
    RESERVED_USERNAMES,
    detect_image_type,
)
from accounts.models import GROWING_STYLE_CHOICES, Profile, ProfileImage
from plants.models import Plant


# The serializers reuse the rules and messages of the HTML forms in forms.py (reserved usernames, 2 MB images,
# https-only links, the same error texts), so the website and the API accept and refuse the same things.


# The write-only image options of ProfileSerializer, taken out of the data before the model fields are saved
IMAGE_OPTION_KEYS = (
    "picture_file", "picture_url", "remove_picture",
    "banner_file", "banner_url", "remove_banner",
)


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField(
        error_messages={"required": "Please enter your email.", "invalid": "Please enter a valid email address."},
    )
    password1 = serializers.CharField(write_only=True, style={"input_type": "password"})
    password2 = serializers.CharField(write_only=True, style={"input_type": "password"})
    agree_terms = serializers.BooleanField(
        write_only=True,
        error_messages={"required": "Please agree to be a kind neighbor to join."},
    )

    def validate_username(self, value):
        # Same checks as UserCreationForm: Django's username rules, and no duplicates (ignoring upper/lower case)
        try:
            User._meta.get_field("username").run_validators(value)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.messages)
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("That username is taken. Please pick another.")
        if value.lower() in RESERVED_USERNAMES:
            raise serializers.ValidationError("That username is reserved. Please pick another.")
        return value

    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("There is already an account with this email. Try logging in instead.")
        return email

    def validate_agree_terms(self, value):
        if not value:
            raise serializers.ValidationError("Please agree to be a kind neighbor to join.")
        return value

    def validate(self, attrs):
        if attrs["password1"] != attrs["password2"]:
            raise serializers.ValidationError({"password2": "The two password fields didn't match."})
        # AUTH_PASSWORD_VALIDATORS, errors are shown on "password1" like on the register page
        candidate = User(username=attrs["username"], email=attrs["email"])
        try:
            password_validation.validate_password(attrs["password1"], candidate)
        except DjangoValidationError as error:
            raise serializers.ValidationError({"password1": list(error.messages)})
        return attrs

    def create(self, validated_data):
        # The post_save signal in models.py makes the Profile
        return User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password1"],
        )


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False, style={"input_type": "password"})

    def validate(self, attrs):
        username, password = attrs["username"], attrs["password"]
        if not User.objects.filter(username=username).exists():
            raise serializers.ValidationError("An account with that username does not exist.", code="no_account")
        # authenticate() returns None for a wrong password and for an inactive account
        user = authenticate(request=self.context.get("request"), username=username, password=password)
        if user is None:
            raise serializers.ValidationError("Wrong username or password. Please try again.", code="invalid_login")
        attrs["user"] = user
        return attrs


class DeleteAccountSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False, style={"input_type": "password"})
    confirm = serializers.BooleanField(
        error_messages={"required": "Please tick the box to confirm."},
    )

    def validate_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("That password isn't right. Please try again.")
        return value

    def validate_confirm(self, value):
        if not value:
            raise serializers.ValidationError("Please tick the box to confirm.")
        return value


class FavoritePlantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plant
        fields = ["id", "name", "slug"]


class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.SerializerMethodField()
    display_name = serializers.CharField(required=False, allow_blank=True, max_length=50)
    initials = serializers.CharField(read_only=True)
    is_owner = serializers.SerializerMethodField()
    stats = serializers.SerializerMethodField()

    favorite_plant = serializers.PrimaryKeyRelatedField(
        queryset=Plant.objects.all(), allow_null=True, required=False,
    )
    favorite_plant_detail = FavoritePlantSerializer(source="favorite_plant", read_only=True)
    growing_style = serializers.ChoiceField(choices=GROWING_STYLE_CHOICES, allow_blank=True, required=False)

    # What is saved now. Uploaded photos are stored with a relative address, which is turned into a full link here.
    profile_picture = serializers.SerializerMethodField()
    cover_image = serializers.SerializerMethodField()

    # Write-only: the three ways to change each image (upload a photo, paste a link, remove it)
    picture_file = serializers.FileField(write_only=True, required=False)
    picture_url = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=500)
    remove_picture = serializers.BooleanField(write_only=True, required=False)
    banner_file = serializers.FileField(write_only=True, required=False)
    banner_url = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=500)
    remove_banner = serializers.BooleanField(write_only=True, required=False)

    class Meta:
        model = Profile
        fields = [
            "username", "email", "display_name", "initials", "bio", "location",
            "favorite_plant", "favorite_plant_detail", "growing_style", "avatar_color",
            "profile_picture", "cover_image",
            "picture_file", "picture_url", "remove_picture",
            "banner_file", "banner_url", "remove_banner",
            "is_owner", "stats", "created_at", "updated_at",
        ]
        read_only_fields = ["avatar_color", "created_at", "updated_at"]

    # ---- reading ----

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # display_name lives on the User (first_name), or is the username when empty, like Profile.display_name
        data["display_name"] = instance.display_name
        return data

    def _absolute(self, link):
        request = self.context.get("request")
        if link.startswith("/") and request is not None:
            return request.build_absolute_uri(link)
        return link

    def get_profile_picture(self, profile):
        return self._absolute(profile.profile_picture)

    def get_cover_image(self, profile):
        return self._absolute(profile.cover_image)

    def _is_owner(self, profile):
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and request.user == profile.user)

    def get_is_owner(self, profile):
        return self._is_owner(profile)

    def get_email(self, profile):
        # Like the website: visitors never see the email
        return profile.user.email if self._is_owner(profile) else None

    def get_stats(self, profile):
        # Plain numbers (the website page shows them as "1.2k"). Imported here so apps don't import each other
        # when Django starts, same as get_profile_stats() in views.py.
        from achievements.models import ClaimedBadge
        from garden.models import Post

        user = profile.user
        return {
            "garden_posts": Post.objects.filter(author=user).count(),
            "appreciations": Post.likes.through.objects.filter(post__author=user).count(),
            "achievements": ClaimedBadge.objects.filter(user=user, status="APPROVED").count(),
            "plants_growing": 0,  # until the plants module is connected, same as the website
        }

    # ---- writing ----

    def validate_display_name(self, value):
        return " ".join(value.split())

    def _validate_file(self, upload):
        if upload.size > MAX_IMAGE_SIZE:
            raise serializers.ValidationError("That photo is bigger than 2 MB. Please choose a smaller one.")
        data = upload.read()
        content_type = detect_image_type(data[:16])
        if not content_type:
            raise serializers.ValidationError("Please upload a JPG, PNG or WebP photo.")
        return {"data": data, "content_type": content_type}

    def _validate_https_link(self, url):
        # Only https:// links, because the site runs on https
        if url and not url.startswith("https://"):
            raise serializers.ValidationError(IMAGE_LINK_ERROR)
        if url:
            serializers.URLField(max_length=500, error_messages={"invalid": IMAGE_LINK_ERROR}).run_validation(url)
        return url

    def validate_picture_file(self, value):
        return self._validate_file(value)

    def validate_banner_file(self, value):
        return self._validate_file(value)

    def validate_picture_url(self, value):
        return self._validate_https_link(value)

    def validate_banner_url(self, value):
        return self._validate_https_link(value)

    def update(self, profile, validated_data):
        user = profile.user
        if "display_name" in validated_data:
            user.first_name = validated_data.pop("display_name")
            user.save(update_fields=["first_name"])
        # Image options are handled by hand, like EditProfileForm.save()
        image_options = {key: validated_data.pop(key) for key in IMAGE_OPTION_KEYS if key in validated_data}
        for attr, value in validated_data.items():
            setattr(profile, attr, value)

        for slot, field, kind, url_name in IMAGE_SLOTS:
            upload = image_options.get(f"{slot}_file")
            url = image_options.get(f"{slot}_url")
            remove = image_options.get(f"remove_{slot}")
            touched = upload is not None or url is not None or remove is not None
            if not touched:
                continue  # PATCH that doesn't mention this image leaves it alone
            saved_upload = ProfileImage.objects.filter(profile=profile, kind=kind)
            is_upload = getattr(profile, field).startswith("/")
            if upload:
                # A new photo wins over everything else. "?v=" changes, so browsers do not show the old photo.
                ProfileImage.objects.update_or_create(
                    profile=profile, kind=kind,
                    defaults={"data": upload["data"], "content_type": upload["content_type"]},
                )
                link = reverse(url_name, args=[user.username])
                setattr(profile, field, f"{link}?v={int(time.time())}")
            elif remove:
                saved_upload.delete()
                setattr(profile, field, "")
            elif url:
                saved_upload.delete()
                setattr(profile, field, url)
            elif url is not None and not is_upload:
                # An empty link clears a pasted link. (An upload is kept unless remove is true.)
                setattr(profile, field, "")
        profile.save()
        return profile
