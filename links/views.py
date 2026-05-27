from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from datetime import timedelta
import json

from accounts.services import get_user_for_api_key
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse
from django.shortcuts import render

from .forms import AbuseReportForm, PasswordGateForm, ShortURLCreateForm, ShortURLEditForm
from .models import AbuseReport, ShortURL
from .rate_limits import (
    consume_password_gate_limit,
    consume_session_daily_limit,
    consume_user_daily_limit,
)
from .services import (
    VISIT_INVALID_PASSWORD,
    VISIT_REDIRECT,
    resolve_anonymous_short_url,
    resolve_namespaced_short_url,
    resolve_reported_path,
    visit_anonymous_short_url,
    visit_namespaced_short_url,
)
from .services import generate_random_slug, slug_is_available
from .validators import suggest_slug_variants, validate_safe_slug


def home(request):
    return render(request, "home.html")


def healthz(request):
    return JsonResponse({"status": "ok"})


def json_error(message: str, status: int, **extra):
    payload = {"error": message}
    payload.update(extra)
    return JsonResponse(payload, status=status)


def parse_non_negative_int(value, field_name: str) -> int:
    if value in (None, ""):
        return 0
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be an integer greater than or equal to 0.")
    if parsed < 0:
        raise ValueError(f"{field_name} must be greater than or equal to 0.")
    return parsed


def clean_string(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def serialize_short_url(short_url: ShortURL, request):
    return {
        "id": short_url.pk,
        "short_url": short_url.get_public_url(request),
        "public_path": short_url.get_public_path(),
        "destination_url": short_url.destination_url,
        "title": short_url.title,
        "public_mode": short_url.public_mode,
        "expires_at": short_url.expires_at.isoformat() if short_url.expires_at else None,
        "max_clicks": short_url.max_clicks,
        "password_protected": bool(short_url.password_hash),
    }


@csrf_exempt
def api_shorten(request):
    if request.method != "POST":
        response = json_error("Method not allowed.", status=405)
        response["Allow"] = "POST"
        return response

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        return json_error("Invalid JSON body.", status=400)

    if not isinstance(payload, dict):
        return json_error("JSON body must be an object.", status=400)

    api_key = request.headers.get("X-API-Key", "").strip()
    owner = None
    if api_key:
        owner = get_user_for_api_key(api_key)
        if owner is None:
            return json_error("Invalid API key.", status=401)
    elif not settings.URLBREVE_ANONYMOUS_API_ENABLED:
        return json_error("Anonymous API creation is disabled.", status=403)

    destination_url = clean_string(payload.get("destination_url"))
    if not destination_url:
        return json_error("destination_url is required.", status=400)

    public_mode = payload.get("public_mode") or ShortURL.PublicMode.ANONYMOUS
    if owner is None:
        if public_mode == ShortURL.PublicMode.NAMESPACE:
            return json_error("X-API-Key is required for namespace mode.", status=403)
        public_mode = ShortURL.PublicMode.ANONYMOUS
    elif public_mode not in ShortURL.PublicMode.values:
        return json_error("public_mode must be anonymous or namespace.", status=400)

    if public_mode == ShortURL.PublicMode.NAMESPACE and owner is None:
        return json_error("X-API-Key is required for namespace mode.", status=403)

    try:
        expires_days = parse_non_negative_int(payload.get("expires_days"), "expires_days")
        max_clicks = parse_non_negative_int(payload.get("max_clicks"), "max_clicks")
    except ValueError as exc:
        return json_error(str(exc), status=400)

    if owner is None:
        limit_result = consume_session_daily_limit(
            request,
            "api-anonymous-shorten",
            settings.URLBREVE_ANONYMOUS_DAILY_LIMIT,
        )
    else:
        limit_result = consume_user_daily_limit(
            "api-key-shorten",
            owner.pk,
            settings.URLBREVE_API_KEY_DAILY_LIMIT,
        )
    if not limit_result.allowed:
        return json_error("Rate limit exceeded.", status=429, limit=limit_result.limit)

    slug = clean_string(payload.get("slug"))
    if slug:
        try:
            validate_safe_slug(slug)
        except ValidationError:
            return json_error("Invalid slug.", status=400)
        if not slug_is_available(slug, public_mode, owner=owner):
            return json_error(
                "Slug already exists.",
                status=409,
                suggestions=suggest_slug_variants(slug),
            )
    else:
        slug = generate_random_slug(public_mode, owner=owner)

    short_url = ShortURL(
        owner=owner,
        destination_url=destination_url,
        slug=slug,
        title=clean_string(payload.get("title"))[:200],
        public_mode=public_mode,
        expires_at=timezone.now() + timedelta(days=expires_days) if expires_days else None,
        max_clicks=max_clicks,
    )

    password = clean_string(payload.get("password"))
    if password:
        short_url.password_hash = make_password(str(password))

    try:
        short_url.full_clean()
    except ValidationError as exc:
        return json_error("Invalid fields.", status=400, details=exc.message_dict)

    try:
        short_url.save()
    except IntegrityError:
        return json_error(
            "Slug already exists.",
            status=409,
            suggestions=suggest_slug_variants(slug),
        )

    return JsonResponse(serialize_short_url(short_url, request), status=201)


def unavailable(request):
    return render(
        request,
        "links/unavailable.html",
        {"reported_path": request.path},
        status=404,
    )


def render_password_gate(request, form):
    return render(
        request,
        "links/password_gate.html",
        {
            "form": form,
            "reported_path": request.path,
        },
    )


def abuse_report(request):
    if request.method == "POST":
        form = AbuseReportForm(request.POST)
        if form.is_valid():
            limit_result = consume_session_daily_limit(
                request,
                "abuse-report",
                settings.URLBREVE_REPORT_SESSION_DAILY_LIMIT,
            )
            if limit_result.allowed:
                reported_path, short_url = resolve_reported_path(
                    form.cleaned_data["reported_path"],
                )
                AbuseReport.objects.create(
                    short_url=short_url,
                    reported_path=reported_path,
                    reason=form.cleaned_data["reason"],
                    details=form.cleaned_data["details"],
                )
                return render(request, "links/report_done.html")
            form.add_error(None, "Has alcanzado el limite diario de reportes.")
    else:
        form = AbuseReportForm(
            initial={"reported_path": request.GET.get("path", "")},
        )

    return render(request, "links/report_form.html", {"form": form})


def handle_public_redirect(request, short_url, visit_func):
    if short_url is None or not short_url.is_available:
        return unavailable(request)

    if short_url.password_hash:
        if request.method == "POST":
            form = PasswordGateForm(request.POST)
            if form.is_valid():
                limit_result = consume_password_gate_limit(
                    request,
                    short_url.pk,
                    settings.URLBREVE_PASSWORD_GATE_SESSION_LIMIT,
                )
                if not limit_result.allowed:
                    form.add_error("password", "Demasiados intentos. Intentalo mas tarde.")
                    return render_password_gate(request, form)
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
            limit_result = consume_user_daily_limit(
                "web-shorten",
                request.user.pk,
                settings.URLBREVE_AUTHENTICATED_DAILY_LIMIT,
            )
            if limit_result.allowed:
                short_url = form.save()
                messages.success(request, "URL corta creada.")
                return redirect(short_url)
            form.add_error(None, "Has alcanzado el limite diario de creacion.")
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
