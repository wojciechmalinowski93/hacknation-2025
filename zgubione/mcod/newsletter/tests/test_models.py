from datetime import date

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile

from mcod.newsletter.models import Newsletter


class TestSubscriptionModel:

    def test_resign_newsletter_absolute_url_with_proper_lang(self, newsletter_subscription):
        assert newsletter_subscription.resign_newsletter_absolute_url.startswith(
            f"{settings.BASE_URL}/{newsletter_subscription.lang}/"
        )

    def test_subscribe_confirm_absolute_url_with_proper_lang(self, newsletter_subscription):
        assert newsletter_subscription.subscribe_confirm_absolute_url.startswith(
            f"{settings.BASE_URL}/{newsletter_subscription.lang}/"
        )

    def test_upload_cp1250_encoded_file(self, admin):
        nl = Newsletter.objects.create(
            file=SimpleUploadedFile(
                "test.html",
                '<html><head></head><body>ąśćężź <a href="#">Resign</a>'
                ' <a href="#">Rezygnacja</a></body></html>'.encode("cp1250"),
                content_type="text/html",
            ),
            title="test-title",
            planned_sending_date=date.today(),
            created_by=admin,
        )
        nl.clean()
