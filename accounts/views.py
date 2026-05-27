from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import RegistrationForm, UserProfileForm
from .services import ensure_user_profile


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

    return render(request, "accounts/profile_form.html", {"form": form})
