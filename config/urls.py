from django.contrib import admin
from django.urls import include, path

from links import views as link_views


urlpatterns = [
    path("", link_views.home, name="home"),
    path("", include("accounts.urls")),
    path("links/", include("links.urls")),
    path("api/shorten/", link_views.api_shorten, name="api_shorten"),
    path("api/links/", link_views.api_links, name="api_links"),
    path("report/", link_views.abuse_report, name="abuse_report"),
    path("healthz/", link_views.healthz, name="healthz"),
    path("admin/", admin.site.urls),
    path("a/<slug:slug>/", link_views.public_anonymous_redirect, name="anonymous_redirect"),
    path(
        "<str:namespace>/<slug:slug>/",
        link_views.public_namespaced_redirect,
        name="namespaced_redirect",
    ),
]
