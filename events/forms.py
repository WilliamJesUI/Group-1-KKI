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


class EventForm(ModelForm):
    # The model stores start_time and end_time as full date + time values.
    # The form asks for one date and two times, like the Figma design, and combines them in clean().
    date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "class": PICKER_CLASS}),
        error_messages={"required": "Please pick a date."},
    )
    start = forms.TimeField(
        widget=forms.TimeInput(attrs={"type": "time", "class": PICKER_CLASS, "aria-label": "Start time"}),
        error_messages={"required": "Please pick a start time."},
    )
    end = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={"type": "time", "class": PICKER_CLASS, "aria-label": "End time"}),
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
            "cover_photo_url": {"invalid": "Please paste a full image link, starting with https://"},
        }

    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get("date")
        start = cleaned_data.get("start")
        end = cleaned_data.get("end")

        if date and start:
            # Turn the date and times into Jakarta time values for the model
            cleaned_data["start_time"] = timezone.make_aware(datetime.combine(date, start))
            cleaned_data["end_time"] = None
            if end:
                if end < start:
                    self.add_error("end", "The end time has to be after the start time.")
                else:
                    cleaned_data["end_time"] = timezone.make_aware(datetime.combine(date, end))
        return cleaned_data
