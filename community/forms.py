from django import forms
from .models import Question

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields =    ["title", "body"]
        widgets = {
            "title" : forms.TextInput(attrs={"placeholder": "e.g. Why are my tomato leaves curling?", 
                                       "class": "w-full rounded-full border-2 border-ink bg-white px-5 py-3",}),
            "body" : forms.Textarea(attrs={"rows" : 5, "placeholder" : "Describe what is happening to your plant...", 
                                           "class": "w-full rounded-[11px] border-2 border-ink bg-white px-5 py-3",}),
        }