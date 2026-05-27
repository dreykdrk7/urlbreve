from django.contrib import admin

from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "public_namespace", "prefer_public_namespace", "updated_at")
    search_fields = ("user__username", "user__email", "public_namespace")
    list_filter = ("prefer_public_namespace",)
