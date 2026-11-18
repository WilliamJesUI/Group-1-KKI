
from rest_framework import serializers

from garden.models import Post
from plants.models import Plant
from events.models import Event


def absolute_url(request, url):
    if not url:
        return ""

    if request is None:
        return url

    return request.build_absolute_uri(url)


class GardenPostSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    username = serializers.CharField(
        source="author.username",
        read_only=True,
    )
    age = serializers.CharField(
        source="age_label",
        read_only=True,
    )
    plant_name = serializers.SerializerMethodField()
    plant_slug = serializers.SerializerMethodField()
    photo_url = serializers.SerializerMethodField()
    like_count = serializers.IntegerField(read_only=True)
    comment_count = serializers.IntegerField(read_only=True)
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            "id",
            "author_name",
            "username",
            "age",
            "caption",
            "plant_name",
            "plant_slug",
            "photo_url",
            "like_count",
            "comment_count",
            "is_liked",
            "created_at",
        ]

    def get_author_name(self, obj):
        return obj.author.get_full_name() or obj.author.username

    def get_plant_name(self, obj):
        return obj.plant.name if obj.plant else ""

    def get_plant_slug(self, obj):
        return obj.plant.slug if obj.plant else ""

    def get_photo_url(self, obj):
        return absolute_url(
            self.context.get("request"),
            obj.photo_src,
        )

    def get_is_liked(self, obj):
        return bool(getattr(obj, "is_liked", False))


class GardenPlantSerializer(serializers.ModelSerializer):
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = Plant
        fields = [
            "id",
            "name",
            "scientific_name",
            "category",
            "difficulty",
            "description",
            "photo_url",
            "slug",
        ]

    def get_photo_url(self, obj):
        return absolute_url(
            self.context.get("request"),
            obj.card_image_url,
        )


class GardenEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = [
            "id",
            "name",
            "start_time",
            "location",
        ]
