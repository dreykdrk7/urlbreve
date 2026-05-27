from django.contrib import admin
from django.urls import include, path

from links import views as link_views


urlpatterns = [
    path("", link_views.home, name="home"),
    path("", include("accounts.urls")),
    path("links/", include("links.urls")),
    path("healthz/", link_views.healthz, name="healthz"),
    path("admin/", admin.site.urls),
]
