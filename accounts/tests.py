from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from config.settings import database_from_url

from .models import UserProfile
from .services import (
    generate_api_key,
    get_user_for_api_key,
    hash_api_key,
    verify_api_key,
)


User = get_user_model()


class SettingsParsingTests(SimpleTestCase):
    def test_database_url_decodes_percent_encoded_credentials(self):
        config = database_from_url(
            "postgres://urlbreve:p%40ss%2Fword@db:5432/urlbreve_prod?sslmode=require",
        )

        self.assertEqual(config["NAME"], "urlbreve_prod")
        self.assertEqual(config["USER"], "urlbreve")
        self.assertEqual(config["PASSWORD"], "p@ss/word")
        self.assertEqual(config["HOST"], "db")
        self.assertEqual(config["PORT"], "5432")
        self.assertEqual(config["OPTIONS"], {"sslmode": "require"})


class RegistrationTests(TestCase):
    def test_registration_creates_user_profile(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "username": "alice",
                "email": "",
                "password1": "StrongPass123",
                "password2": "StrongPass123",
            },
        )

        self.assertRedirects(response, reverse("accounts:dashboard"))
        user = User.objects.get(username="alice")
        self.assertEqual(user.profile.public_namespace, "alice")

    def test_namespace_collision_does_not_break_registration(self):
        existing_user = User.objects.create_user(username="existing")
        UserProfile.objects.create(user=existing_user, public_namespace="taken")

        response = self.client.post(
            reverse("accounts:register"),
            {
                "username": "taken",
                "password1": "StrongPass123",
                "password2": "StrongPass123",
            },
        )

        self.assertRedirects(response, reverse("accounts:dashboard"))
        user = User.objects.get(username="taken")
        self.assertEqual(user.profile.public_namespace, "taken-2")


class DashboardTests(TestCase):
    def test_dashboard_requires_authentication(self):
        response = self.client.get(reverse("accounts:dashboard"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])

    def test_dashboard_renders_for_authenticated_user(self):
        user = User.objects.create_user(username="bob", password="StrongPass123")
        UserProfile.objects.create(user=user, public_namespace="bob")
        self.client.login(username="bob", password="StrongPass123")

        response = self.client.get(reverse("accounts:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "bob")
        self.assertContains(response, "Dashboard")


class ProfileEditTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="carol", password="StrongPass123")
        self.profile = UserProfile.objects.create(
            user=self.user,
            public_namespace="carol",
        )
        self.client.login(username="carol", password="StrongPass123")

    def test_namespace_validation_rejects_invalid_value(self):
        response = self.client.post(
            reverse("accounts:profile_edit"),
            {
                "public_namespace": "bad namespace",
                "prefer_public_namespace": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "public_namespace",
            "Use 3-64 lowercase ASCII letters, numbers, hyphens or "
            "underscores; start and end with a letter or number.",
        )
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.public_namespace, "carol")

    def test_namespace_edit_updates_profile(self):
        response = self.client.post(
            reverse("accounts:profile_edit"),
            {
                "public_namespace": "carol-links",
                "prefer_public_namespace": "on",
            },
        )

        self.assertRedirects(response, reverse("accounts:dashboard"))
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.public_namespace, "carol-links")
        self.assertTrue(self.profile.prefer_public_namespace)

    def test_namespace_edit_rejects_collision(self):
        other_user = User.objects.create_user(username="other")
        UserProfile.objects.create(user=other_user, public_namespace="taken")

        response = self.client.post(
            reverse("accounts:profile_edit"),
            {"public_namespace": "taken"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "public_namespace",
            "This namespace is already taken or reserved.",
        )


class APIKeyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="dora", password="StrongPass123")
        self.profile = UserProfile.objects.create(
            user=self.user,
            public_namespace="dora",
        )
        self.client.login(username="dora", password="StrongPass123")

    def test_api_key_helpers_hash_verify_and_resolve_user(self):
        raw_key = generate_api_key()
        key_hash = hash_api_key(raw_key)
        self.profile.api_key_hash = key_hash
        self.profile.save(update_fields=["api_key_hash"])

        self.assertTrue(raw_key.startswith("ub_"))
        self.assertNotEqual(raw_key, key_hash)
        self.assertTrue(verify_api_key(raw_key, key_hash))
        self.assertFalse(verify_api_key("wrong", key_hash))
        self.assertEqual(get_user_for_api_key(raw_key), self.user)

    def test_rotate_api_key_shows_raw_key_once(self):
        response = self.client.post(reverse("accounts:api_key_rotate"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ub_")
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.api_key_hash)

        followup = self.client.get(reverse("accounts:profile_edit"))
        self.assertNotContains(followup, "ub_")

    def test_revoke_api_key_clears_hash(self):
        self.profile.api_key_hash = hash_api_key(generate_api_key())
        self.profile.save(update_fields=["api_key_hash"])

        response = self.client.post(reverse("accounts:api_key_revoke"))

        self.assertRedirects(response, reverse("accounts:profile_edit"))
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.api_key_hash, "")
