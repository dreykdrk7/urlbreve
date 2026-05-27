from django.contrib import admin

from .models import ShortURL, ShortURLDailyStats


@admin.register(ShortURL)
class ShortURLAdmin(admin.ModelAdmin):
    list_display = (
        "slug",
        "public_mode",
        "owner",
        "is_active",
        "is_disabled",
        "click_count",
        "created_at",
    )
    list_filter = ("public_mode", "is_active", "is_disabled")
    search_fields = ("slug", "destination_url", "title", "owner__username")
    readonly_fields = ("created_at", "updated_at", "last_clicked_at")


@admin.register(ShortURLDailyStats)
class ShortURLDailyStatsAdmin(admin.ModelAdmin):
    list_display = ("short_url", "date", "clicks")
    list_filter = ("date",)
    search_fields = ("short_url__slug",)
