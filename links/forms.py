from django import forms
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from datetime import timedelta

from accounts.services import ensure_user_profile

from .models import AbuseReport, ShortURL
from .services import generate_random_slug, slug_is_available
from .validators import suggest_slug_variants


class ShortURLCreateForm(forms.ModelForm):
    slug = forms.CharField(max_length=64, required=False, strip=False)
    expires_days = forms.IntegerField(
        label="Dias hasta expirar",
        min_value=0,
        initial=0,
        required=False,
    )
    max_clicks = forms.IntegerField(min_value=0, initial=0, required=False)
    password = forms.CharField(
        label="Contrasena",
        required=False,
        strip=False,
        widget=forms.PasswordInput(render_value=False),
    )

    class Meta:
        model = ShortURL
        fields = (
            "destination_url",
            "slug",
            "title",
            "public_mode",
            "max_clicks",
        )
        labels = {
            "destination_url": "URL destino",
            "slug": "Slug",
            "title": "Titulo",
            "public_mode": "Modo publico",
            "max_clicks": "Limite de clicks",
        }

    def __init__(self, *args, owner, **kwargs):
        self.owner = owner
        self.profile = ensure_user_profile(owner)
        super().__init__(*args, **kwargs)
        self.instance.owner = owner
        self.fields["public_mode"].initial = (
            ShortURL.PublicMode.NAMESPACE
            if self.profile.prefer_public_namespace
            else ShortURL.PublicMode.ANONYMOUS
        )

    def clean(self):
        cleaned_data = super().clean()
        public_mode = cleaned_data.get("public_mode")
        slug = cleaned_data.get("slug")

        if public_mode == ShortURL.PublicMode.NAMESPACE and not self.profile.public_namespace:
            self.add_error("public_mode", "Namespace mode requires a public namespace.")
            return cleaned_data

        if public_mode and slug:
            if not slug_is_available(slug, public_mode, owner=self.owner):
                suggestions = ", ".join(suggest_slug_variants(slug))
                self.add_error(
                    "slug",
                    f"This slug is already in use. Try: {suggestions}.",
                )
        elif public_mode:
            cleaned_data["slug"] = generate_random_slug(public_mode, owner=self.owner)

        expires_days = cleaned_data.get("expires_days") or 0
        cleaned_data["expires_at"] = (
            timezone.now() + timedelta(days=expires_days)
            if expires_days > 0
            else None
        )
        cleaned_data["max_clicks"] = cleaned_data.get("max_clicks") or 0
        return cleaned_data

    def save(self, commit: bool = True):
        instance = super().save(commit=False)
        instance.owner = self.owner
        instance.slug = self.cleaned_data["slug"]
        instance.expires_at = self.cleaned_data["expires_at"]
        instance.max_clicks = self.cleaned_data["max_clicks"]

        password = self.cleaned_data.get("password")
        if password:
            instance.password_hash = make_password(password)

        if commit:
            instance.save()
        return instance


class ShortURLEditForm(forms.ModelForm):
    expires_at = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
        input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"],
    )
    max_clicks = forms.IntegerField(min_value=0, initial=0, required=False)
    password = forms.CharField(
        label="Contrasena",
        required=False,
        strip=False,
        widget=forms.PasswordInput(render_value=False),
    )
    clear_password = forms.BooleanField(label="Quitar contrasena", required=False)

    class Meta:
        model = ShortURL
        fields = (
            "destination_url",
            "title",
            "expires_at",
            "max_clicks",
            "is_active",
        )
        labels = {
            "destination_url": "URL destino",
            "title": "Titulo",
            "expires_at": "Expira en",
            "max_clicks": "Limite de clicks",
            "is_active": "Activa",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.expires_at:
            self.initial["expires_at"] = self.instance.expires_at.strftime("%Y-%m-%dT%H:%M")

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data["max_clicks"] = cleaned_data.get("max_clicks") or 0
        return cleaned_data

    def save(self, commit: bool = True):
        instance = super().save(commit=False)
        instance.max_clicks = self.cleaned_data["max_clicks"]

        if self.cleaned_data.get("clear_password"):
            instance.password_hash = ""
        elif self.cleaned_data.get("password"):
            instance.password_hash = make_password(self.cleaned_data["password"])

        if commit:
            instance.save()
        return instance


class PasswordGateForm(forms.Form):
    password = forms.CharField(
        label="Contrasena",
        strip=False,
        widget=forms.PasswordInput(render_value=False),
    )


class AbuseReportForm(forms.Form):
    reported_path = forms.CharField(
        label="Ruta reportada",
        max_length=512,
        help_text="Ejemplo: /a/demo/ o /namespace/demo/",
    )
    reason = forms.ChoiceField(
        label="Motivo",
        choices=AbuseReport.Reason.choices,
    )
    details = forms.CharField(
        label="Detalles",
        max_length=1000,
        required=False,
        widget=forms.Textarea(attrs={"rows": 5}),
        help_text="Opcional. No incluyas datos personales.",
    )
