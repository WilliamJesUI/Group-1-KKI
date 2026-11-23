from django.urls import reverse
from django.utils.html import strip_tags
from django.utils.text import Truncator
from django.utils.timesince import timesince
from rest_framework import serializers

from .models import Question, Answer


class QuestionSerializer(serializers.ModelSerializer):
    # Author
    author_name = serializers.SerializerMethodField()
    author_url = serializers.SerializerMethodField()
    author_initials = serializers.CharField(source="author.profile.initials", read_only=True)
    author_avatar_class = serializers.CharField(source="author.profile.avatar_bg_class", read_only=True)
    author_picture = serializers.CharField(source="author.profile.profile_picture", read_only=True, allow_null=True)

    # Display helpers
    time_ago = serializers.SerializerMethodField()
    excerpt = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    # Plant
    plant_name = serializers.CharField(source="plant.name", read_only=True, allow_null=True)
    plant_slug = serializers.CharField(source="plant.slug", read_only=True, allow_null=True)
    plant_url = serializers.SerializerMethodField()

    # Counts (come from .annotate() in the view)
    answer_count = serializers.IntegerField(read_only=True)
    vote_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Question
        fields = [
            "id", "author", "author_name", "author_url", "author_initials",
            "author_avatar_class", "author_picture",
            "title", "body", "excerpt",
            "created_at", "updated_at", "time_ago", "url",
            "voters",
            "plant", "plant_name", "plant_slug", "plant_url",
            "answer_count", "vote_count",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "voters", "author"]

    # --- Output helpers ---

    def get_author_name(self, obj):
        return obj.author.get_full_name() or obj.author.username

    def get_author_url(self, obj):
        return reverse("profile:show_user_profile", args=[obj.author.username])

    def get_time_ago(self, obj):
        return f"{timesince(obj.created_at)} ago"

    def get_excerpt(self, obj):
        return Truncator(obj.body).chars(70)

    def get_url(self, obj):
        return reverse("community:show_question_thread", args=[obj.id])

    def get_plant_url(self, obj):
        if not obj.plant:
            return None
        return reverse("encyclopedia:detail", args=[obj.plant.slug])

    # --- Input validation ---

    def validate_title(self, value):
        value = strip_tags(value).strip()
        if not value:
            raise serializers.ValidationError("Question title cannot be empty.")
        return value

    def validate_body(self, value):
        return strip_tags(value).strip()


        
class AnswerSerializer(serializers.ModelSerializer):
    # Author
    author_name = serializers.SerializerMethodField()
    author_url = serializers.SerializerMethodField()
    author_initials = serializers.CharField(source="author.profile.initials", read_only=True)
    author_avatar_class = serializers.CharField(source="author.profile.avatar_bg_class", read_only=True)
    author_picture = serializers.CharField(source="author.profile.profile_picture", read_only=True, allow_null=True)

    # Display helpers
    time_ago = serializers.SerializerMethodField()

    # Counts and voting (vote_count comes from .annotate() in the view)
    vote_count = serializers.IntegerField(read_only=True)
    is_voted = serializers.SerializerMethodField()

    # Permissions (only control which buttons show; the real checks are in the permission class)
    can_edit = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()

    # URLs
    url = serializers.SerializerMethodField()
    vote_url = serializers.SerializerMethodField()

    class Meta:
        model = Answer
        fields = [
            "id", "question", "body",
            "author", "author_name", "author_url",
            "author_initials", "author_avatar_class", "author_picture",
            "created_at", "updated_at", "time_ago",
            "vote_count", "is_voted",
            "can_edit", "can_delete",
            "url", "vote_url",
        ]
        # Only model fields need listing here; declared fields above are already read-only
        read_only_fields = ["id", "question", "author", "created_at", "updated_at"]

    # --- Output helpers ---
    def _user(self):
        request = self.context.get("request")
        return request.user if request and request.user.is_authenticated else None

    def get_author_name(self, obj):
        return obj.author.get_full_name() or obj.author.username

    def get_author_url(self, obj):
        return reverse("profile:show_user_profile", args=[obj.author.username])

    def get_time_ago(self, obj):
        return f"{timesince(obj.created_at)} ago"

    def get_is_voted(self, obj):
        user = self._user()
        return bool(user) and user in obj.voters.all()   # uses the prefetch

    def get_can_edit(self, obj):
        user = self._user()
        return bool(user) and obj.author_id == user.id

    def get_can_delete(self, obj):
        user = self._user()
        return bool(user) and (obj.author_id == user.id or user.is_staff)

    def get_url(self, obj):
        return reverse("community:api:answer-detail", args=[obj.id])

    def get_vote_url(self, obj):
        return reverse("community:vote_answer_ajax", args=[obj.id])

    # --- Input validation ---
    def validate_body(self, value):
        value = strip_tags(value).strip()
        if not value:
            raise serializers.ValidationError("Answer cannot be empty.")
        return value