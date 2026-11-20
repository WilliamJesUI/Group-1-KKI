from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from events.forms import PlantSelect
from plants.models import Plant
from achievements.models import Goal, ProgressLog

# Tailwind classes for the inputs, the same ones events/forms.py uses (from Figma).
# aria-invalid:border-danger turns the border red when the field has an error.
INPUT_CLASS = (
    "h-11 w-full rounded-full border-2 border-ink bg-surface px-4 text-sm placeholder:text-muted "
    "focus:border-brand focus:ring-1 focus:ring-brand focus:outline-none aria-invalid:border-danger"
)
TEXTAREA_CLASS = (
    "w-full rounded-2xl border-2 border-ink bg-surface px-4 py-3 text-sm placeholder:text-muted "
    "focus:border-brand focus:ring-1 focus:ring-brand focus:outline-none aria-invalid:border-danger"
)
# Figma: the "Why this goal?" and "Note" boxes are 112px (h-28) tall
NOTE_CLASS = TEXTAREA_CLASS + " h-28 resize-none"
# The plant list has its own arrow (added in the template), so the browser's arrow is hidden.
# The first option ("Choose a plant...") is shown in the muted colour like a placeholder.
SELECT_CLASS = INPUT_CLASS + " appearance-none pr-10 has-[option[value='']:checked]:text-muted [&>option]:text-ink"
# Date inputs sit inside a rounded box, so they have no border of their own
PICKER_CLASS = "min-w-0 flex-1 bg-transparent text-sm focus:outline-none [&::-webkit-calendar-picker-indicator]:hidden"

# Temporary list, taken from the Encyclopedia frame in Figma.
# When the Encyclopedia module is merged, Goal.plant becomes a ForeignKey to its Plant model and this list goes away.

class GoalForm(forms.ModelForm):
    plant = forms.ModelChoiceField(
        queryset=Plant.objects.all(),
        empty_label="Choose a plant...",
        widget=PlantSelect(attrs={"class": INPUT_CLASS}),
        error_messages={"required": "Please choose a plant."},
    )

    class Meta:
        model = Goal
        fields = ["title", "plant", "target", "finish_by", "reason"]
        labels = {"title": "Goal", "target": "How many times?", "finish_by": "Finish by", "reason": "Why this goal?"}
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "e.g. Harvest 5 tomatoes", "class": INPUT_CLASS}),
            "target": forms.NumberInput(attrs={"placeholder": "e.g. 5", "min": 1, "class": INPUT_CLASS}),
            # format=... makes the saved date show up in the right shape when the form is opened for editing
            "finish_by": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date", "class": PICKER_CLASS}),
            "reason": forms.Textarea(attrs={"placeholder": "A little note to future you.", "class": NOTE_CLASS}),
        }
        error_messages = {
            "title": {"required": "Please give your goal a name."},
            "target": {"required": "Please say how many times."},
        }

    def clean_finish_by(self):
        finish_by = self.cleaned_data["finish_by"]
        # Only check a date the user just picked, so an old goal with a past date can still be edited
        if finish_by and "finish_by" in self.changed_data and finish_by < timezone.localdate():
            raise ValidationError("Please pick today or a later date.")
        return finish_by

    def clean_target(self):
        target = self.cleaned_data["target"]
        # When editing, the goal can't be set lower than what is already logged
        if self.instance.pk and target < self.instance.done:
            raise ValidationError(f"You've already logged {self.instance.done}, so the goal can't be lower than that.")
        return target


class ProgressLogForm(forms.ModelForm):
    class Meta:
        model = ProgressLog
        fields = ["amount", "date", "note"]
        labels = {"amount": "How many this time?", "date": "Date", "note": "Note"}
        widgets = {
            "amount": forms.NumberInput(attrs={"placeholder": "1", "min": 1, "class": INPUT_CLASS}),
            "date": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date", "class": PICKER_CLASS}),
            "note": forms.Textarea(attrs={"placeholder": "e.g. Picked 2 ripe ones this morning.", "class": NOTE_CLASS}),
        }
        error_messages = {
            "amount": {"required": "Please say how many."},
            "date": {"required": "Please pick a date."},
        }

    def clean_date(self):
        date = self.cleaned_data["date"]
        if date > timezone.localdate():
            raise ValidationError("The date can't be in the future.")
        return date