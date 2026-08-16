from rest_framework import serializers

from .models import Amenity, FavoriteStadium, Review, Stadium, StadiumImage


class StadiumCreateSerializer(serializers.ModelSerializer):
    amenity_keys = serializers.SlugRelatedField(
        source="amenities",
        slug_field="key",
        queryset=Amenity.objects.all(),
        many=True,
        required=False,
    )

    class Meta:
        model = Stadium
        fields = (
            "id",
            "name",
            "district",
            "city",
            "address",
            "main_image_url",
            "base_price_per_hour",
            "base_slot_price",
            "amenity_keys",
        )
        read_only_fields = ("id",)

    def create(self, validated_data):
        amenities = validated_data.pop("amenities", [])
        stadium = Stadium.objects.create(**validated_data)
        if amenities:
            stadium.amenities.set(amenities)
        return stadium


class AmenitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Amenity
        fields = ("key", "label")


class StadiumImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = StadiumImage
        fields = ("image_url", "sort_order")


class ReviewSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.full_name", read_only=True)
    author_avatar = serializers.CharField(source="author.avatar_url", read_only=True)

    class Meta:
        model = Review
        fields = ("id", "author_name", "author_avatar", "rating", "text", "created_at")
        read_only_fields = ("id", "created_at")


class StadiumListSerializer(serializers.ModelSerializer):
    rating = serializers.FloatField(read_only=True)
    reviews_count = serializers.IntegerField(read_only=True)
    amenities = AmenitySerializer(many=True, read_only=True)
    is_favorite = serializers.SerializerMethodField()

    class Meta:
        model = Stadium
        fields = (
            "id",
            "name",
            "district",
            "city",
            "main_image_url",
            "rating",
            "reviews_count",
            "address",
            "amenities",
            "base_price_per_hour",
            "base_slot_price",
            "is_favorite",
        )

    def get_is_favorite(self, obj):
        user = self.context["request"].user
        if not user.is_authenticated:
            return False
        return obj.id in self.context.get("favorite_ids", set())


class StadiumDetailSerializer(StadiumListSerializer):
    gallery = StadiumImageSerializer(many=True, read_only=True)
    top_review = serializers.SerializerMethodField()

    class Meta(StadiumListSerializer.Meta):
        fields = StadiumListSerializer.Meta.fields + (
            "gallery",
            "owner_name",
            "owner_verified",
            "owner_avatar_url",
            "top_review",
        )

    def get_top_review(self, obj):
        review = obj.reviews.order_by("-rating", "-created_at").first()
        if not review:
            return None
        return ReviewSerializer(review).data


class FavoriteStadiumSerializer(serializers.ModelSerializer):
    class Meta:
        model = FavoriteStadium
        fields = ("id", "stadium", "created_at")
        read_only_fields = ("id", "created_at")
