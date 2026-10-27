import time

from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.urls import reverse

from accounts.models import GROWING_STYLE_CHOICES, Profile, ProfileImage

# Tailwind classes from the Input / Textarea components in Figma. Same as events/forms.py, with h-12 on the auth pages.
# aria-invalid:border-danger turns the border red when a field has an error (see AriaInvalidMixin below).
INPUT_CLASS = (
    "h-12 w-full rounded-full border-2 border-ink bg-surface px-4 text-sm placeholder:text-muted "
    "focus:border-brand focus:ring-1 focus:ring-brand focus:outline-none aria-invalid:border-danger"
)
TEXTAREA_CLASS = (
    "w-full rounded-2xl border-2 border-ink bg-surface px-4 py-3 text-sm placeholder:text-muted "
    "focus:border-brand focus:ring-1 focus:ring-brand focus:outline-none aria-invalid:border-danger"
)
CHECKBOX_CLASS = "size-5 shrink-0 rounded-md border-2 border-ink accent-brand focus:ring-1 focus:ring-brand focus:outline-none"

IMAGE_LINK_ERROR = "Please paste a full image link, starting with https://"
# The real file input is hidden: the dropzone in templates/accounts/_image_field.html is its label
FILE_CLASS = "sr-only"
MAX_IMAGE_SIZE = 2 * 1024 * 1024  # 2 MB
ACCEPTED_TYPES = "image/jpeg,image/png,image/webp"

# /profile/<username>/ is the public page, so /profile/edit/ and /profile/delete/ would clash with users with those names
RESERVED_USERNAMES = {"edit", "delete"}


class AriaInvalidMixin:
    # After validation, mark every field that has an error with aria-invalid="true".
    # The Tailwind class aria-invalid:border-danger then turns its border red, and screen readers announce the error.
    def full_clean(self):
        super().full_clean()
        for name in self.errors:
            if name in self.fields:
                self.fields[name].widget.attrs["aria-invalid"] = "true"


class RegisterForm(AriaInvalidMixin, UserCreationForm):
    # UserCreationForm already gives us username, password1, password2 and checks the password with
    # AUTH_PASSWORD_VALIDATORS (min 8 characters, not too common, not all numbers, not like the username).
    email = forms.EmailField(
        error_messages={"required": "Please enter your email.", "invalid": "Please enter a valid email address."},
    )
    agree_terms = forms.BooleanField(
        label="I agree to be a kind neighbor",
        error_messages={"required": "Please agree to be a kind neighbor to join."},
        widget=forms.CheckboxInput(attrs={"class": CHECKBOX_CLASS}),
    )
    field_order = ["username", "email", "password1", "password2", "agree_terms"]

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")
        error_messages = {"username": {"unique": "That username is taken. Please pick another."}}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Labels and placeholders from the Figma "Join the garden" screen
        self.fields["username"].label = "Username"
        self.fields["username"].widget.attrs.update({"class": INPUT_CLASS, "placeholder": "Pick a name people will see"})
        self.fields["email"].label = "Email"
        self.fields["email"].widget.attrs.update({"class": INPUT_CLASS, "placeholder": "you@example.com", "autocomplete": "email"})
        self.fields["password1"].label = "Password"
        # Django's list of password rules is HTML and looks broken in this layout. The rules that fail are shown as errors.
        self.fields["password1"].help_text = ""
        self.fields["password1"].widget.attrs.update({"class": INPUT_CLASS, "placeholder": "At least 8 characters"})
        self.fields["password2"].label = "Confirm password"
        self.fields["password2"].widget.attrs.update({"class": INPUT_CLASS, "placeholder": "Type it again"})

    def _post_clean(self):
        # Django checks the password rules (too short, too common, too similar to the username...) in its own
        # _post_clean and puts any errors on "Confirm password". They are about the password itself, so we do the
        # same check here and show the errors on "Password" instead. A mismatch between the two fields still shows
        # on "Confirm password", because that is done by clean_password2.
        forms.ModelForm._post_clean(self)
        password = self.cleaned_data.get("password2")
        if password:
            try:
                password_validation.validate_password(password, self.instance)
            except forms.ValidationError as error:
                self.add_error("password1", error)

    def full_clean(self):
        super().full_clean()
        # The two password boxes belong together, so when the password is refused, both get the red border
        if "password1" in self.errors:
            self.fields["password2"].widget.attrs["aria-invalid"] = "true"

    def clean_username(self):
        # Django's own clean_username only checks for duplicates (ignoring upper/lower case) and returns nothing,
        # so we read the value from cleaned_data ourselves and return it.
        super().clean_username()
        # .get(), because when the username is already taken Django's check records the error and removes the value
        username = self.cleaned_data.get("username")
        if username and username.lower() in RESERVED_USERNAMES:
            raise forms.ValidationError("That username is reserved. Please pick another.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        # Django's User does not make email unique by itself, so we check it here (ignoring upper/lower case)
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("There is already an account with this email. Try logging in instead.")
        return email


class LoginForm(AriaInvalidMixin, AuthenticationForm):
    # AuthenticationForm does the real work: it calls authenticate() and refuses inactive users.
    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": "Wrong username or password. Please try again.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Username"
        self.fields["username"].widget.attrs.update({"class": INPUT_CLASS, "placeholder": "e.g. bengrows"})
        self.fields["password"].label = "Password"
        self.fields["password"].widget.attrs.update({"class": INPUT_CLASS, "placeholder": "Your password"})

    def clean(self):
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")
        # Check the username first, so we can say that the account does not exist. This is a form-wide error, so it
        # shows in the pink box above the form (like a wrong password) and no field turns red.
        if username and password and not User.objects.filter(username=username).exists():
            raise forms.ValidationError("An account with that username does not exist.", code="no_account")
        # The username exists, so what is left is a wrong password (or an inactive account)
        return super().clean()


def detect_image_type(head):
    # Look at the first bytes of the file, because the file name and the browser's content type can be faked
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    return None


# (name used in the form fields, Profile field that holds the link, ProfileImage kind, URL name that serves the upload)
IMAGE_SLOTS = (
    ("picture", "profile_picture", ProfileImage.AVATAR, "profile:picture"),
    ("banner", "cover_image", ProfileImage.BANNER, "profile:banner"),
)


def make_image_fields(label):
    # The three ways to change one image: upload a photo, paste a link, or remove it
    return {
        "file": forms.FileField(
            required=False, label="Upload a photo",
            widget=forms.FileInput(attrs={"class": FILE_CLASS, "accept": ACCEPTED_TYPES}),
        ),
        "url": forms.URLField(
            required=False, max_length=500, label="Paste an image link",
            widget=forms.URLInput(attrs={"placeholder": "https://images.pexels.com/photos/...", "class": INPUT_CLASS}),
            error_messages={"invalid": IMAGE_LINK_ERROR},
        ),
        "remove": forms.BooleanField(
            required=False, label=f"Remove my current {label}",
            widget=forms.CheckboxInput(attrs={"class": CHECKBOX_CLASS}),
        ),
    }


class EditProfileForm(AriaInvalidMixin, forms.ModelForm):
    # The display name is saved on the User (as first_name, which the navbar already shows), not on the Profile.
    display_name = forms.CharField(
        required=False, max_length=50, label="Display name",
        widget=forms.TextInput(attrs={"placeholder": "e.g. Pro Gardener", "class": INPUT_CLASS}),
        help_text="Shown instead of your username. Leave it empty to use your username.",
    )
    # The text fields are normal model fields. The two images are handled by hand (see save()),
    # because each one can come from an uploaded file or from a pasted link.
    picture_file = make_image_fields("profile picture")["file"]
    picture_url = make_image_fields("profile picture")["url"]
    remove_picture = make_image_fields("profile picture")["remove"]
    banner_file = make_image_fields("profile banner")["file"]
    banner_url = make_image_fields("profile banner")["url"]
    remove_banner = make_image_fields("profile banner")["remove"]

    class Meta:
        model = Profile
        fields = ["bio", "location", "favorite_plant", "growing_style"]
        labels = {"favorite_plant": "Favorite plant", "growing_style": "Growing style"}
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 4, "placeholder": "Tell other gardeners about yourself", "class": TEXTAREA_CLASS}),
            "location": forms.TextInput(attrs={"placeholder": "e.g. South Jakarta", "class": INPUT_CLASS}),
            "favorite_plant": forms.TextInput(attrs={"placeholder": "e.g. Cherry Tomato", "class": INPUT_CLASS}),
            "growing_style": forms.Select(attrs={"class": INPUT_CLASS}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Replace Django's "---------" with friendlier text for the empty choice
        self.fields["growing_style"].choices = [("", "Choose a growing style")] + GROWING_STYLE_CHOICES
        self.initial["display_name"] = self.instance.user.first_name
        # For each image: what is saved now (the template shows a preview), and was it uploaded or pasted?
        # An uploaded photo is saved as one of our own addresses, which starts with "/".
        for slot, field, kind, url_name in IMAGE_SLOTS:
            current = getattr(self.instance, field)
            setattr(self, f"current_{slot}", current)
            setattr(self, f"{slot}_is_upload", current.startswith("/"))
            # Only a pasted link goes back into the link box. Our own upload address would confuse people.
            self.initial[f"{slot}_url"] = "" if current.startswith("/") else current

    def _clean_file(self, name):
        upload = self.cleaned_data.get(name)
        if not upload:
            return None
        if upload.size > MAX_IMAGE_SIZE:
            raise forms.ValidationError("That photo is bigger than 2 MB. Please choose a smaller one.")
        data = upload.read()
        content_type = detect_image_type(data[:16])
        if not content_type:
            raise forms.ValidationError("Please upload a JPG, PNG or WebP photo.")
        return {"data": data, "content_type": content_type}

    def _clean_https_link(self, name):
        url = self.cleaned_data.get(name)
        # A URLField alone also accepts http:// and ftp:// links, and adds http:// to links without one.
        # Only https:// is allowed: our site runs on https, and browsers block or warn about http images there.
        if url and not url.startswith("https://"):
            raise forms.ValidationError(IMAGE_LINK_ERROR)
        return url

    def clean_display_name(self):
        # Remove extra spaces, so "  Kristina   Ayu " becomes "Kristina Ayu"
        return " ".join(self.cleaned_data["display_name"].split())

    def clean_picture_file(self):
        return self._clean_file("picture_file")

    def clean_banner_file(self):
        return self._clean_file("banner_file")

    def clean_picture_url(self):
        return self._clean_https_link("picture_url")

    def clean_banner_url(self):
        return self._clean_https_link("banner_url")

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = profile.user
        user.first_name = self.cleaned_data["display_name"]
        user.save(update_fields=["first_name"])
        for slot, field, kind, url_name in IMAGE_SLOTS:
            upload = self.cleaned_data.get(f"{slot}_file")
            url = self.cleaned_data.get(f"{slot}_url")
            remove = self.cleaned_data.get(f"remove_{slot}")
            saved_upload = ProfileImage.objects.filter(profile=profile, kind=kind)
            if upload:
                # A new photo wins over everything else. "?v=" changes, so browsers do not show the old photo.
                ProfileImage.objects.update_or_create(
                    profile=profile, kind=kind,
                    defaults={"data": upload["data"], "content_type": upload["content_type"]},
                )
                link = reverse(url_name, args=[profile.user.username])
                setattr(profile, field, f"{link}?v={int(time.time())}")
            elif remove:
                saved_upload.delete()
                setattr(profile, field, "")
            elif url:
                saved_upload.delete()
                setattr(profile, field, url)
            elif not getattr(self, f"{slot}_is_upload"):
                # The link box was emptied, so the pasted link is cleared. (An upload is kept unless "Remove" is ticked.)
                setattr(profile, field, "")
        if commit:
            profile.save()
        return profile


class DeleteAccountForm(AriaInvalidMixin, forms.Form):
    # Deleting an account can't be undone, so we ask for the password and a tick, in case the button was pressed by accident
    password = forms.CharField(
        label="Your password",
        strip=False,
        widget=forms.PasswordInput(attrs={"class": INPUT_CLASS, "placeholder": "Your password", "autocomplete": "current-password"}),
    )
    confirm = forms.BooleanField(
        label="I understand this can't be undone",
        error_messages={"required": "Please tick the box to confirm."},
        widget=forms.CheckboxInput(attrs={"class": CHECKBOX_CLASS}),
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not self.user.check_password(password):
            raise forms.ValidationError("That password isn't right. Please try again.")
        return password
