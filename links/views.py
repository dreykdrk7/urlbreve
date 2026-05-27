from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse
from django.shortcuts import render

from .forms import ShortURLCreateForm, ShortURLEditForm
from .models import ShortURL


def home(request):
    return render(request, "home.html")


def healthz(request):
    return JsonResponse({"status": "ok"})


def get_owned_short_url(user, pk: int) -> ShortURL:
    return get_object_or_404(
        ShortURL.objects.select_related("owner__profile"),
        pk=pk,
        owner=user,
        deleted_at__isnull=True,
    )


@login_required
def short_url_create(request):
    if request.method == "POST":
        form = ShortURLCreateForm(request.POST, owner=request.user)
        if form.is_valid():
            short_url = form.save()
            messages.success(request, "URL corta creada.")
            return redirect(short_url)
    else:
        form = ShortURLCreateForm(owner=request.user)

    return render(request, "links/shorturl_form.html", {"form": form, "mode": "create"})


@login_required
def short_url_detail(request, pk: int):
    short_url = get_owned_short_url(request.user, pk)
    return render(request, "links/shorturl_detail.html", {"short_url": short_url})


@login_required
def short_url_edit(request, pk: int):
    short_url = get_owned_short_url(request.user, pk)
    if request.method == "POST":
        form = ShortURLEditForm(request.POST, instance=short_url)
        if form.is_valid():
            form.save()
            messages.success(request, "URL actualizada.")
            return redirect(short_url)
    else:
        form = ShortURLEditForm(instance=short_url)

    return render(
        request,
        "links/shorturl_form.html",
        {
            "form": form,
            "mode": "edit",
            "short_url": short_url,
        },
    )


@login_required
def short_url_delete(request, pk: int):
    short_url = get_owned_short_url(request.user, pk)
    if request.method == "POST":
        short_url.mark_deleted()
        messages.success(request, "URL ocultada.")
        return redirect("accounts:dashboard")

    return render(request, "links/shorturl_confirm_delete.html", {"short_url": short_url})
