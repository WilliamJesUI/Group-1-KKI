from django import forms

# Reuse shared form styles and the plant selector from the Events app.
from events.forms import (
    INPUT_CLASS,
    TEXTAREA_CLASS,
    PlantSelect,
    detect_image_type
)

from garden.models import Comment, PlantOfTheWeek, Post


# Maximum allowed image size: 2 MB.
MAX_PHOTO_SIZE = 2 * 1024 * 1024


class PostForm(forms.ModelForm):
    """Form for creating and editing Garden posts."""

    # Custom field for uploading a photo.
    photo_upload = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={
            "accept": "image/jpeg,image/png,image/webp",
            "class": "peer sr-only"
        }),
    )

    # JavaScript sets this field when the user removes an existing photo.
    remove_photo = forms.BooleanField(
        required=False,
        widget=forms.HiddenInput
    )

    class Meta:
        model = Post
        fields = ["caption", "plant"]

        labels = {
            "caption": "Caption",
            "plant": "Plant"
        }

        widgets = {
            "caption": forms.Textarea(attrs={
                "placeholder": "Share what's growing in your garden...",
                "rows": 4,
                "maxlength": 1000,
                "class": TEXTAREA_CLASS,
            }),

            # Reuses the shared plant selection widget.
            "plant": PlantSelect(attrs={
                "class": INPUT_CLASS
            }),
        }

        error_messages = {
            "caption": {
                "required": "Please write a caption."
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Sets the default text in the plant dropdown.
        self.fields["plant"].empty_label = "Tag a plant..."

    def clean_photo_upload(self):
        # Django calls this method automatically during form validation.
        upload = self.cleaned_data.get("photo_upload")

        if not upload:
            return None

        # Check the uploaded file size.
        if upload.size > MAX_PHOTO_SIZE:
            raise forms.ValidationError(
                "That photo is too big. Please pick one under 2 MB."
            )

        # Read the uploaded image as bytes.
        data = upload.read()

        # Detect the actual image type.
        photo_type = detect_image_type(data)

        if photo_type is None:
            raise forms.ValidationError(
                "Please pick a JPG, PNG or WebP photo."
            )

        return {
            "data": data,
            "type": photo_type
        }


class CommentForm(forms.ModelForm):
    """Form for adding comments to a post."""

    class Meta:
        model = Comment
        fields = ["text"]

        widgets = {
            "text": forms.TextInput(attrs={
                "placeholder": "Write a comment...",
                "maxlength": 1000,
                "class": INPUT_CLASS,
                "aria-label": "Write a comment",
            }),
        }

        error_messages = {
            "text": {
                "required": "Please write a comment first."
            }
        }


class PlantOfTheWeekForm(forms.ModelForm):
    """Form used by moderators to select the plant of the week."""

    class Meta:
        model = PlantOfTheWeek
        fields = ["plant", "short_line"]

        labels = {
            "plant": "Plant",
            "short_line": "Short line (optional)"
        }

        widgets = {
            "plant": PlantSelect(attrs={
                "class": INPUT_CLASS,
                "data-picker-inline": ""
            }),

            "short_line": forms.Textarea(attrs={
                "rows": 3,
                "maxlength": 200,
                "class": TEXTAREA_CLASS
            }),
        }

        error_messages = {
            "plant": {
                "required": "Please pick a plant."
            }
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["plant"].empty_label = "Choose a plant..."