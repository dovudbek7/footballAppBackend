from django.contrib import admin

from .models import Amenity, FavoriteStadium, Review, Stadium, StadiumImage, StadiumSlotTemplate


class StadiumImageInline(admin.TabularInline):
    model = StadiumImage
    extra = 1


class StadiumSlotTemplateInline(admin.TabularInline):
    model = StadiumSlotTemplate
    extra = 1


@admin.register(Stadium)
class StadiumAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "district", "base_price_per_hour", "base_slot_price", "is_active")
    search_fields = ("name", "city", "district")
    filter_horizontal = ("amenities",)
    inlines = [StadiumImageInline, StadiumSlotTemplateInline]


@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ("label", "key")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("stadium", "author", "rating", "created_at")


@admin.register(FavoriteStadium)
class FavoriteStadiumAdmin(admin.ModelAdmin):
    list_display = ("user", "stadium", "created_at")
