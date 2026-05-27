from django.urls import path

from . import views


app_name = "links"

urlpatterns = [
    path("new/", views.short_url_create, name="create"),
    path("<int:pk>/", views.short_url_detail, name="detail"),
    path("<int:pk>/edit/", views.short_url_edit, name="edit"),
    path("<int:pk>/delete/", views.short_url_delete, name="delete"),
]
