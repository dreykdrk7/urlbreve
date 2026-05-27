from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse
from django.shortcuts import render

from .forms import PasswordGateForm, ShortURLCreateForm, ShortURLEditForm
from .models import ShortURL
from .services import (
    VISIT_INVALID_PASSWORD,
    VISIT_REDIRECT,
    resolve_anonymous_short_url,
    resolve_namespaced_short_url,
    visit_anonymous_short_url,
    visit_namespaced_short_url,
)


def home(request):
    return render(request, "home.html")


def healthz(request):
    return JsonResponse({"status": "ok"})


def unavailable(request):
    return render(request, "links/unavailable.html", status=404)


def render_password_gate(request, form):
    return render(request, "links/password_gate.html", {"form": form})


def handle_public_redirect(request, short_url, visit_func):
    if short_url is None or not short_url.is_available:
        return unavailable(request)

    if short_url.password_hash:
        if request.method == "POST":
            form = PasswordGateForm(request.POST)
            if form.is_valid():
                result = visit_func(password=form.cleaned_data["password"])
                if result.status == VISIT_REDIRECT:
                    return redirect(result.destination_url)
                if result.status == VISIT_INVALID_PASSWORD:
                    form.add_error("password", "No pudimos validar la contrasena.")
                    return render_password_gate(request, form)
                return unavailable(request)
        else:
            form = PasswordGateForm()
        return render_password_gate(request, form)

    result = visit_func()
    if result.status != VISIT_REDIRECT:
        return unavailable(request)
    return redirect(result.destination_url)


def public_anonymous_redirect(request, slug: str):
    short_url = resolve_anonymous_short_url(slug)
    return handle_public_redirect(
        request,
        short_url,
        lambda password=None: visit_anonymous_short_url(slug, password=password),
    )


def public_namespaced_redirect(request, namespace: str, slug: str):
    short_url = resolve_namespaced_short_url(namespace, slug)
    return handle_public_redirect(
        request,
        short_url,
        lambda password=None: visit_namespaced_short_url(
            namespace,
            slug,
            password=password,
        ),
    )


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
