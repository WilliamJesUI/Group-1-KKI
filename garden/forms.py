from django import forms
from events.forms import INPUT_CLASS, TEXTAREA_CLASS, PlantSelect, detect_image_type
from garden.models import Comment, PlantOfTheWeek, Post

MAX_PHOTO_SIZE = 2 * 1024 * 1024  # 2 MB, same as the Events cover photo


class PostForm(forms.ModelForm):
    """The "Share your garden" / "Edit post" pop-up (Figma "Overlay / Create a post")."""

    # Not a model field: clean_photo_upload() checks the file and the view saves its bytes on the post
    photo_upload = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={"accept": "image/jpeg,image/png,image/webp", "class": "peer sr-only"}),
    )
    # Set to "True" by garden.js when the owner clicks Remove on the current photo
    remove_photo = forms.BooleanField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Post
        fields = ["caption", "plant"]
        labels = {"caption": "Caption", "plant": "Plant"}
        widgets = {
            "caption": forms.Textarea(attrs={
                "placeholder": "Share what's growing in your garden...",
                "rows": 4,
                "maxlength": 1000,
                "class": TEXTAREA_CLASS,
            }),
            # The same plant picker as the Events theme plant (static/js/plant_picker.js)
            "plant": PlantSelect(attrs={"class": INPUT_CLASS}),
        }
        error_messages = {
            "caption": {"required": "Please write a caption."},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["plant"].empty_label = "Tag a plant..."

    def clean_photo_upload(self):
        upload = self.cleaned_data.get("photo_upload")
        if not upload:
            return None
        if upload.size > MAX_PHOTO_SIZE:
            raise forms.ValidationError("That photo is too big. Please pick one under 2 MB.")
        data = upload.read()
        photo_type = detect_image_type(data)
        if photo_type is None:
            raise forms.ValidationError("Please pick a JPG, PNG or WebP photo.")
        return {"data": data, "type": photo_type}


class CommentForm(forms.ModelForm):
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
        error_messages = {"text": {"required": "Please write a comment first."}}


class PlantOfTheWeekForm(forms.ModelForm):
    """The admin-only "Plant of the week" pop-up (Figma "Overlay / Set plant of the week (admin)")."""

    class Meta:
        model = PlantOfTheWeek
        fields = ["plant", "short_line"]
        labels = {"plant": "Plant", "short_line": "Short line (optional)"}
        widgets = {
            # data-picker-inline: the plant list opens inside this short pop-up instead of over it (plant_picker.js)
            "plant": PlantSelect(attrs={"class": INPUT_CLASS, "data-picker-inline": ""}),
            "short_line": forms.Textarea(attrs={"rows": 3, "maxlength": 200, "class": TEXTAREA_CLASS}),
        }
        error_messages = {"plant": {"required": "Please pick a plant."}}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["plant"].empty_label = "Choose a plant..."
