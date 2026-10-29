import uuid
from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse
from django.utils import timezone

# Create your models here.
# Question model
class Question(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="questions")
    title = models.CharField(max_length=256)
    body = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    voters = models.ManyToManyField(User)
    plant = models.ForeignKey(
        "plants.Plant",            # change "plants" to the app that holds Plant
        on_delete=models.SET_NULL,
        null=True,
        blank=True,                # the tag is optional
        related_name="questions",
    )

    def __str__(self):
        return f"{self.title} {self.body} {self.created_at}"

# Answer model
class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="answers")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="answers")
    body = models.TextField(blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    voters = models.ManyToManyField(User)