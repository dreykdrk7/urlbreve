from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from .validators import suggest_slug_variants, validate_http_https_url, validate_safe_slug


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
