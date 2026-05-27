from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile

from .models import ShortURL
from .validators import suggest_slug_variants, validate_http_https_url, validate_safe_slug


User = get_user_model()


class SlugValidatorTests(SimpleTestCase):
    def test_accepts_safe_ascii_slug(self):
        validate_safe_slug("abc-123_ok")

    def test_rejects_unicode_and_spaces(self):
        with self.assertRaises(ValidationError):
            validate_safe_slug("café")
        with self.assertRaises(ValidationError):
            validate_safe_slug("abc 123")

    def test_rejects_reserved_slug(self):
        with self.assertRaises(ValidationError):
            validate_safe_slug("admin")


class DestinationURLValidatorTests(SimpleTestCase):
    def test_accepts_http_and_https_only(self):
        validate_http_https_url("https://example.com/a")
        validate_http_https_url("http://example.com/a")
        with self.assertRaises(ValidationError):
            validate_http_https_url("ftp://example.com/a")


class SlugSuggestionTests(SimpleTestCase):
    def test_suggestions_are_deterministic(self):
        self.assertEqual(
            suggest_slug_variants("hello world", count=3),
            ["hello-world-2", "hello-world-3", "hello-world-4"],
        )


class ShortURLManagementTests(TestCase):
    def create_user(self, username: str):
        user = User.objects.create_user(username=username, password="StrongPass123")
        UserProfile.objects.create(user=user, public_namespace=username)
        return user

    def login(self, user):
        self.client.login(username=user.username, password="StrongPass123")

    def post_create(self, **overrides):
        data = {
            "destination_url": "https://example.com/page",
            "slug": "abc123",
            "title": "Example",
            "public_mode": ShortURL.PublicMode.ANONYMOUS,
            "expires_days": "0",
            "max_clicks": "0",
            "password": "",
        }
        data.update(overrides)
        return self.client.post(reverse("links:create"), data)

    def test_authenticated_user_can_create_anonymous_url(self):
        user = self.create_user("alice")
        self.login(user)

        response = self.post_create(slug="anon123")

        short_url = ShortURL.objects.get(slug="anon123")
        self.assertRedirects(response, short_url.get_absolute_url())
        self.assertEqual(short_url.owner, user)
        self.assertEqual(short_url.public_mode, ShortURL.PublicMode.ANONYMOUS)
        self.assertEqual(short_url.get_public_path(), "/a/anon123/")

    def test_authenticated_user_can_create_namespace_url(self):
        user = self.create_user("bob")
        self.login(user)

        response = self.post_create(
            slug="ns123",
            public_mode=ShortURL.PublicMode.NAMESPACE,
        )

        short_url = ShortURL.objects.get(slug="ns123")
        self.assertRedirects(response, short_url.get_absolute_url())
        self.assertEqual(short_url.public_mode, ShortURL.PublicMode.NAMESPACE)
        self.assertEqual(short_url.get_public_path(), "/bob/ns123/")

    def test_blank_slug_generates_random_code(self):
        user = self.create_user("carol")
        self.login(user)

        response = self.post_create(slug="")

        short_url = ShortURL.objects.get()
        self.assertRedirects(response, short_url.get_absolute_url())
        self.assertEqual(len(short_url.slug), 8)
        validate_safe_slug(short_url.slug)

    def test_anonymous_slug_collision_returns_error(self):
        user = self.create_user("dana")
        self.login(user)
        ShortURL.objects.create(
            owner=user,
            destination_url="https://example.com/one",
            slug="dup",
            public_mode=ShortURL.PublicMode.ANONYMOUS,
        )

        response = self.post_create(slug="dup")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This slug is already in use")
        self.assertContains(response, "dup-2")
        self.assertEqual(ShortURL.objects.filter(slug="dup").count(), 1)

    def test_namespace_slug_collision_for_same_owner_returns_error(self):
        user = self.create_user("eric")
        self.login(user)
        ShortURL.objects.create(
            owner=user,
            destination_url="https://example.com/one",
            slug="same",
            public_mode=ShortURL.PublicMode.NAMESPACE,
        )

        response = self.post_create(
            slug="same",
            public_mode=ShortURL.PublicMode.NAMESPACE,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This slug is already in use")
        self.assertEqual(
            ShortURL.objects.filter(
                slug="same",
                public_mode=ShortURL.PublicMode.NAMESPACE,
            ).count(),
            1,
        )

    def test_same_namespace_slug_allowed_for_different_users(self):
        first = self.create_user("first")
        second = self.create_user("second")
        ShortURL.objects.create(
            owner=first,
            destination_url="https://example.com/one",
            slug="shared",
            public_mode=ShortURL.PublicMode.NAMESPACE,
        )
        self.login(second)

        response = self.post_create(
            slug="shared",
            public_mode=ShortURL.PublicMode.NAMESPACE,
        )

        short_url = ShortURL.objects.get(owner=second, slug="shared")
        self.assertRedirects(response, short_url.get_absolute_url())
        self.assertEqual(
            ShortURL.objects.filter(
                slug="shared",
                public_mode=ShortURL.PublicMode.NAMESPACE,
            ).count(),
            2,
        )

    def test_destination_url_only_allows_http_and_https(self):
        user = self.create_user("fran")
        self.login(user)

        response = self.post_create(destination_url="ftp://example.com/file")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ShortURL.objects.count(), 0)

    def test_edit_does_not_allow_slug_change(self):
        user = self.create_user("gina")
        self.login(user)
        short_url = ShortURL.objects.create(
            owner=user,
            destination_url="https://example.com/one",
            slug="fixed",
            public_mode=ShortURL.PublicMode.ANONYMOUS,
        )

        response = self.client.post(
            reverse("links:edit", kwargs={"pk": short_url.pk}),
            {
                "destination_url": "https://example.com/two",
                "title": "Changed",
                "expires_at": "",
                "max_clicks": "5",
                "is_active": "on",
                "slug": "changed",
            },
        )

        self.assertRedirects(response, short_url.get_absolute_url())
        short_url.refresh_from_db()
        self.assertEqual(short_url.slug, "fixed")
        self.assertEqual(short_url.destination_url, "https://example.com/two")
        self.assertEqual(short_url.max_clicks, 5)

    def test_soft_delete_hides_url_from_dashboard(self):
        user = self.create_user("helen")
        self.login(user)
        short_url = ShortURL.objects.create(
            owner=user,
            destination_url="https://example.com/one",
            slug="hide-me",
            public_mode=ShortURL.PublicMode.ANONYMOUS,
        )

        response = self.client.post(reverse("links:delete", kwargs={"pk": short_url.pk}))

        self.assertRedirects(response, reverse("accounts:dashboard"))
        short_url.refresh_from_db()
        self.assertIsNotNone(short_url.deleted_at)
        dashboard = self.client.get(reverse("accounts:dashboard"))
        self.assertNotContains(dashboard, "/a/hide-me/")
