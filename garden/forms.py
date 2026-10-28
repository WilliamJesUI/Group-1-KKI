from django import forms
from .models import Post, Comment

class PostForm(forms.ModelForm):
    categories = forms.MultipleChoiceField(
        choices=Post.PLANT_CATEGORIES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Post
        fields = ["caption", "image_url", "categories", "plant_tag"]
        widgets = {
            "caption": forms.Textarea(attrs={"placeholder": "Share what's growing...", "rows": 3}),
            "image_url": forms.URLInput(attrs={"placeholder": "https://example.com/photo.jpg"}),
            "plant_tag": forms.TextInput(attrs={"placeholder": "e.g. Cherry Tomato"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            selected = self.instance.categories or []
            if not selected and self.instance.category:
                selected = [self.instance.category]
            self.fields["categories"].initial = selected

    def save(self, commit=True):
        post = super().save(commit=False)
        selected = self.cleaned_data.get("categories", [])
        post.categories = list(selected)
        post.category = selected[0] if selected else ""
        if commit:
            post.save()
            self.save_m2m()
        return post

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["text"]
        widgets = {
            "text": forms.Textarea(attrs={"placeholder": "Write a comment...", "rows": 2, "maxlength": 1500}),
        }