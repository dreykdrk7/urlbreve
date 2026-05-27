from django.contrib import admin
from django.utils import timezone

from .models import AbuseReport, ShortURL, ShortURLDailyStats


@admin.action(description="Disable selected links")
def disable_selected_links(modeladmin, request, queryset):
    updated = queryset.update(is_disabled=True, updated_at=timezone.now())
    if modeladmin and request:
        modeladmin.message_user(request, f"{updated} links disabled.")


@admin.action(description="Enable selected links")
def enable_selected_links(modeladmin, request, queryset):
    updated = queryset.update(is_disabled=False, updated_at=timezone.now())
    if modeladmin and request:
        modeladmin.message_user(request, f"{updated} links enabled.")


@admin.action(description="Disable links attached to selected reports")
def disable_reported_links(modeladmin, request, queryset):
    now = timezone.now()
    links = ShortURL.objects.filter(abuse_reports__in=queryset).distinct()
    updated_links = links.update(is_disabled=True, updated_at=now)
    queryset.filter(short_url__isnull=False).update(
        status=AbuseReport.Status.ACTION_TAKEN,
        reviewed_at=now,
    )
    if modeladmin and request:
        modeladmin.message_user(request, f"{updated_links} reported links disabled.")


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
    list_filter = ("public_mode", "is_active", "is_disabled", "created_at")
    search_fields = ("slug", "destination_url", "title", "owner__username")
    readonly_fields = ("created_at", "updated_at", "last_clicked_at")
    actions = (disable_selected_links, enable_selected_links)


@admin.register(ShortURLDailyStats)
class ShortURLDailyStatsAdmin(admin.ModelAdmin):
    list_display = ("short_url", "date", "clicks")
    list_filter = ("date",)
    search_fields = ("short_url__slug",)


@admin.register(AbuseReport)
class AbuseReportAdmin(admin.ModelAdmin):
    list_display = (
        "reported_path",
        "short_url",
        "reason",
        "status",
        "created_at",
        "reviewed_at",
    )
    list_filter = ("status", "reason", "created_at")
    search_fields = (
        "reported_path",
        "details",
        "admin_notes",
        "short_url__slug",
        "short_url__destination_url",
    )
    readonly_fields = ("created_at",)
    actions = (disable_reported_links,)
