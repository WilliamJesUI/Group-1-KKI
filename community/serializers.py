from django.utils.html import strip_tags
from rest_framework import serializers

from .models import Question, Answer
from plants.models import Plant

class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ["id", "author", "title", "body", "created_at", "updated_at", "voters", "plant"]
        read_only_fields = ["id", "created_at", "updated_at", "voters", "author"]

    def validate_title(self, value):
        value = strip_tags(value).strip()
        if not value:
            raise serializers.ValidationError("Question title cannot be empty.")
        return value

    def validate_body(self, value):
        value = strip_tags(value).strip()
        return value


        
class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = ["id", "question", "author", "body", "created_at", "updated_at", "voters"]
        read_only_fields = ["id", "question", "author", "created_at", "updated_at", "voters"]

    def validate_body(self, value):
        value = strip_tags(value).strip()
        if not value:
            raise serializers.ValidationError("Answer cannot be empty.")
        return value
    

