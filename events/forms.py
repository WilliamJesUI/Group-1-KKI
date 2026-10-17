from datetime import datetime
from django import forms
from django.forms import ModelForm
from django.utils import timezone
from events.models import Event

# Tailwind classes for the inputs, taken from the Input and Textarea components in Figma.
# aria-invalid:border-danger turns the border red when the field has an error.
INPUT_CLASS = (
    "h-11 w-full rounded-full border-2 border-ink bg-surface px-4 text-sm placeholder:text-muted "
    "focus:border-brand focus:ring-1 focus:ring-brand focus:outline-none aria-invalid:border-danger"
)
TEXTAREA_CLASS = (
    "w-full rounded-2xl border-2 border-ink bg-surface px-4 py-3 text-sm placeholder:text-muted "
    "focus:border-brand focus:ring-1 focus:ring-brand focus:outline-none aria-invalid:border-danger"
)
# Date and time inputs sit inside a rounded box, so they have no border of their own
PICKER_CLASS = "min-w-0 flex-1 bg-transparent text-sm focus:outline-none [&::-webkit-calendar-picker-indicator]:hidden"

MAX_COVER_SIZE = 2 * 1024 * 1024  # 2 MB
COVER_LINK_ERROR = "Please paste a full image link, starting with https://"


def detect_image_type(data):
    # Every JPG, PNG and WebP file starts with the same few bytes, so we check those
    # instead of trusting the file name (anyone can rename a file to .png).
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


class EventForm(ModelForm):
    # The model stores start_time and end_time as full date + time values.
    # The form asks for one date and two times, like the Figma design, and combines them in clean().
    # format=... makes the saved value show up in the right shape when the form is opened for editing
    date = forms.DateField(
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date", "class": PICKER_CLASS}),
        error_messages={"required": "Please pick a date."},
    )
    start = forms.TimeField(
        widget=forms.TimeInput(format="%H:%M", attrs={"type": "time", "class": PICKER_CLASS, "aria-label": "Start time"}),
        error_messages={"required": "Please pick a start time."},
    )
    end = forms.TimeField(
        required=False,
        widget=forms.TimeInput(format="%H:%M", attrs={"type": "time", "class": PICKER_CLASS, "aria-label": "End time"}),
    )
    # Set to true by JS when the host clicks "Remove" on their current photo while editing
    remove_cover = forms.BooleanField(required=False, widget=forms.HiddenInput)
    # Not a model field: the photo is checked here and then saved into cover_image in the view
    cover_upload = forms.FileField(
        required=False,
        # sr-only hides the plain file button, the drag and drop box in the template is shown instead
        widget=forms.FileInput(attrs={"accept": "image/jpeg,image/png,image/webp", "class": "peer sr-only"}),
    )

    class Meta:
        model = Event
        fields = ["name", "location", "description", "what_to_bring", "cover_photo_url"]
        labels = {
            "name": "Event name",
            "what_to_bring": "What to bring",
            "cover_photo_url": "Cover photo",
        }
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. Community Seed Swap", "class": INPUT_CLASS}),
            "location": forms.TextInput(attrs={"placeholder": "e.g. Menteng Urban Farm", "class": INPUT_CLASS}),
            "description": forms.Textarea(attrs={
                "placeholder": "What will people do?",
                "rows": 4,
                "class": TEXTAREA_CLASS,
            }),
            "what_to_bring": forms.Textarea(attrs={
                "placeholder": "Seeds in labelled envelopes\nA reusable bag",
                "rows": 3,
                "class": TEXTAREA_CLASS,
            }),
            "cover_photo_url": forms.URLInput(attrs={
                "placeholder": "https://images.pexels.com/photos/...",
                "class": INPUT_CLASS,
            }),
        }
        error_messages = {
            "name": {"required": "Please give your event a name."},
            "location": {"required": "Please add a location."},
            "description": {"required": "Please tell people what the event is about."},
            "cover_photo_url": {"invalid": COVER_LINK_ERROR},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # When editing an existing event, fill the date and time boxes from its start_time and end_time.
        # Checks start_time, not pk: our UUID id is made right away, so even a new, unsaved event has a pk.
        if self.instance.start_time:
            start_time = timezone.localtime(self.instance.start_time)
            self.initial["date"] = start_time.date()
            self.initial["start"] = start_time.time()
            if self.instance.end_time:
                self.initial["end"] = timezone.localtime(self.instance.end_time).time()

    def clean_cover_upload(self):
        upload = self.cleaned_data.get("cover_upload")
        if not upload:
            return None
        if upload.size > MAX_COVER_SIZE:
            raise forms.ValidationError("That photo is too big. Please pick one under 2 MB.")
        data = upload.read()
        image_type = detect_image_type(data)
        if image_type is None:
            raise forms.ValidationError("Please pick a JPG, PNG or WebP photo.")
        # Hand the bytes and the type to the view, which saves them on the event
        return {"data": data, "type": image_type}

    def clean_cover_photo_url(self):
        url = self.cleaned_data.get("cover_photo_url")
        # A URLField alone also accepts http:// and ftp:// links, and adds http:// to links without one.
        # Only https:// is allowed: our site runs on https, and browsers block or warn about http images there.
        if url and not url.startswith("https://"):
            raise forms.ValidationError(COVER_LINK_ERROR)
        return url

    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get("date")
        start = cleaned_data.get("start")
        end = cleaned_data.get("end")

        if date and start:
            # Turn the date and times into Jakarta time values for the model
            start_time = timezone.make_aware(datetime.combine(date, start))
            cleaned_data["start_time"] = start_time
            cleaned_data["end_time"] = None

            # No new events in the past. Only checked when the start changed, so a host can still fix the
            # text of an event that already happened. For a new event, self.instance.start_time is None.
            old_start = self.instance.start_time
            if old_start:
                # The form only has hours and minutes, so ignore the seconds when comparing
                old_start = old_start.replace(second=0, microsecond=0)
            if start_time != old_start and start_time < timezone.now():
                self.add_error("date", "This date and time has already passed. Please pick a later one.")

            if end:
                # <= so an end time equal to the start time is refused too, like the message says
                if end <= start:
                    self.add_error("end", "The end time has to be after the start time.")
                else:
                    cleaned_data["end_time"] = timezone.make_aware(datetime.combine(date, end))
        return cleaned_data
