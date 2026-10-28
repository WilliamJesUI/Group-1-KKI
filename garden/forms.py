from django import forms
from .models import Post, Comment

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['caption', 'image_url', 'category', 'plant_tag']
        widgets = {
            'caption': forms.Textarea(attrs={
                'placeholder': "Share what's growing in your garden...",
                'rows': 2,
                'class': 'w-full bg-transparent resize-none focus:outline-none text-sm'
            }),
            'image_url': forms.URLInput(attrs={
                'placeholder': 'Paste image URL (optional)',
                'class': 'w-full text-xs text-ink-soft bg-transparent focus:outline-none'
            }),
            'category': forms.Select(attrs={
                'class': 'w-full text-xs text-ink-soft bg-transparent focus:outline-none cursor-pointer'
            }),
            'plant_tag': forms.TextInput(attrs={
                'placeholder': 'Specific plant (optional, e.g. Cherry Tomato)',
                'class': 'w-full text-xs text-ink-soft bg-transparent focus:outline-none'
            })
        }
        labels = {
            'caption': '',
            'image_url': '',
            'category': '',
            'plant_tag': ''
        }

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
        widgets = {
            'text': forms.TextInput(attrs={
                'placeholder': 'Write a comment...',
                'class': 'w-full text-sm bg-transparent focus:outline-none'
            })
        }
        labels = {'text': ''}