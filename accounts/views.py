from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import RegistrationForm, UserProfileForm
from .services import ensure_user_profile, generate_api_key, hash_api_key


def register(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            ensure_user_profile(user)
            login(request, user)
            messages.success(request, "Cuenta creada.")
            return redirect("accounts:dashboard")
    else:
        form = RegistrationForm()

    return render(request, "accounts/register.html", {"form": form})


@login_required
def dashboard(request):
    profile = ensure_user_profile(request.user)
    short_urls = (
        request.user.short_urls.filter(deleted_at__isnull=True)
        .select_related("owner__profile")
        .order_by("-created_at")
    )
    return render(
        request,
        "accounts/dashboard.html",
        {
            "profile": profile,
            "short_url_count": short_urls.count(),
            "short_urls": short_urls,
        },
    )


@login_required
def profile_edit(request):
    profile = ensure_user_profile(request.user)
    if request.method == "POST":
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Perfil actualizado.")
            return redirect("accounts:dashboard")
    else:
        form = UserProfileForm(instance=profile)

    return render(request, "accounts/profile_form.html", {"form": form, "profile": profile})


@login_required
def api_key_rotate(request):
    if request.method != "POST":
        return redirect("accounts:profile_edit")

    profile = ensure_user_profile(request.user)
    raw_key = generate_api_key()
    profile.api_key_hash = hash_api_key(raw_key)
    profile.save(update_fields=["api_key_hash", "updated_at"])
    form = UserProfileForm(instance=profile)
    messages.success(request, "API key generada. Guardala ahora; no volvera a mostrarse.")
    return render(
        request,
        "accounts/profile_form.html",
        {
            "form": form,
            "profile": profile,
            "new_api_key": raw_key,
        },
    )


@login_required
def api_key_revoke(request):
    if request.method == "POST":
        profile = ensure_user_profile(request.user)
        profile.api_key_hash = ""
        profile.save(update_fields=["api_key_hash", "updated_at"])
        messages.success(request, "API key revocada.")
    return redirect("accounts:profile_edit")
