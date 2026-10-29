from django import forms
from .models import Question, Answer
from plants.models import Plant

class QuestionForm(forms.ModelForm):
    plant = forms.ModelChoiceField(
        queryset=Plant.objects.order_by("name"),
        required=False,
        empty_label="No plant tag",
        widget=forms.Select(attrs={
            "class": "w-full rounded-[11px] border-2 border-ink bg-white px-5 py-3",
        }),
    )

    class Meta:
        model = Question
        fields =    ["title", "body", "plant"]
        widgets = {
            "title" : forms.TextInput(attrs={"placeholder": "e.g. Why are my tomato leaves curling?", "autocomplete":"off",
                                       "class": "w-full rounded-full border-2 border-ink bg-white px-5 py-3",}),
            "body" : forms.Textarea(attrs={"rows" : 5, "placeholder" : "Describe what is happening to your plant...", 
                                           "class": "w-full rounded-[11px] border-2 border-ink bg-white px-5 py-3",}),
        }

class AnswerForm(forms.ModelForm):
    class Meta:
        model = Answer
        fields = ["body"]
        widgets = {
            "body" : forms.Textarea(attrs={"rows" : 7, "placeholder" : "Share what worked for you...", 
                                            "class": "w-full rounded-[11px] border-2 border-ink bg-white px-5 py-3",}),
        }