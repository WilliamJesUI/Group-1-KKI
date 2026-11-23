from django.utils.html import strip_tags
from rest_framework import serializers

from growyourgarden.permissions import can_delete

from .models import Question, Answer


class QuestionSerializer(serializers.ModelSerializer):
    # Author
    author_name = serializers.SerializerMethodField()
    author_initials = serializers.CharField(source="author.profile.initials", read_only=True)
    author_picture = serializers.CharField(source="author.profile.profile_picture", read_only=True, allow_null=True)

    # Plant
    plant_name = serializers.CharField(source="plant.name", read_only=True, allow_null=True)
    plant_slug = serializers.CharField(source="plant.slug", read_only=True, allow_null=True)

    # Counts and voting (answer_count and vote_count come from .annotate() in the view)
    answer_count = serializers.IntegerField(read_only=True)
    vote_count = serializers.IntegerField(read_only=True)
    is_voted = serializers.SerializerMethodField()

    # Permissions (only control which buttons show; the real checks are in the permission class)
    can_edit = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = [
            "id", "title", "body",
            "author", "author_name", "author_initials", "author_picture",
            "plant", "plant_name", "plant_slug",
            "created_at", "updated_at",
            "answer_count", "vote_count", "is_voted",
            "can_edit", "can_delete",
        ]
        # Only model fields need listing; declared fields above are already read-only
        read_only_fields = ["id", "author", "created_at", "updated_at"]

    # --- Output helpers ---
    def _user(self):
        request = self.context.get("request")
        return request.user if request and request.user.is_authenticated else None

    def get_author_name(self, obj):
        return obj.author.get_full_name() or obj.author.username

    def get_is_voted(self, obj):
        user = self._user()
        return bool(user) and user in obj.voters.all()   # uses the prefetch

    def get_can_edit(self, obj):
        user = self._user()
        return bool(user) and obj.author_id == user.id

    def get_can_delete(self, obj):
        user = self._user()
        return bool(user) and can_delete(user, obj.author)

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
    author_initials = serializers.CharField(source="author.profile.initials", read_only=True)
    author_picture = serializers.CharField(source="author.profile.profile_picture", read_only=True, allow_null=True)

    # Counts and voting (vote_count comes from .annotate() in the view)
    vote_count = serializers.IntegerField(read_only=True)
    is_voted = serializers.SerializerMethodField()

    # Permissions (only control which buttons show; the real checks are in the permission class)
    can_edit = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()

    class Meta:
        model = Answer
        fields = [
            "id", "question", "body",
            "author", "author_name", "author_initials", "author_picture",
            "created_at", "updated_at",
            "vote_count", "is_voted",
            "can_edit", "can_delete",
        ]
        read_only_fields = ["id", "question", "author", "created_at", "updated_at"]

    # --- Output helpers ---
    def _user(self):
        request = self.context.get("request")
        return request.user if request and request.user.is_authenticated else None

    def get_author_name(self, obj):
        return obj.author.get_full_name() or obj.author.username

    def get_is_voted(self, obj):
        user = self._user()
        return bool(user) and user in obj.voters.all()   # uses the prefetch

    def get_can_edit(self, obj):
        user = self._user()
        return bool(user) and obj.author_id == user.id

    def get_can_delete(self, obj):
        user = self._user()
        return bool(user) and can_delete(user, obj.author)

    # --- Input validation ---
    def validate_body(self, value):
        value = strip_tags(value).strip()
        if not value:
            raise serializers.ValidationError("Answer cannot be empty.")
        return value