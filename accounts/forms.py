from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import UserProfile
from .services import namespace_is_available


User = get_user_model()


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "password1", "password2")

    def save(self, commit: bool = True):
        user = super().save(commit=False)
        user.email = self.cleaned_data.get("email", "")
        if commit:
            user.save()
        return user


class UserProfileForm(forms.ModelForm):
    public_namespace = forms.CharField(max_length=64, required=True)

    class Meta:
        model = UserProfile
        fields = ("public_namespace", "prefer_public_namespace")

    def clean_public_namespace(self):
        namespace = self.cleaned_data["public_namespace"].strip().lower()
        if not namespace_is_available(namespace, profile=self.instance):
            raise forms.ValidationError("This namespace is already taken or reserved.")
        return namespace
