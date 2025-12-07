import os

from django.conf import settings
from django.test import override_settings
from django.utils.translation import override

from mcod.core.tests.helpers.tasks import run_on_commit_events
from mcod.showcases.models import ShowcaseProposal


class TestApplicationsTasks:
    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.filebased.EmailBackend",
        EMAIL_FILE_PATH="/tmp/app-messages",
    )
    def test_sending_application_proposal(self, datasets):
        image_b64 = [
            "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAMAAAAoLQ9TAAAAElBMVEUAAAAAAACAgAC9vb3AwAD/",
            "/8AMUnRBAAAAAXRSTlMAQObYZgAAAEhJREFUeNqlzoEJwCAMRFETzv1XbvLlboEGmvIfIh6matd8",
            "zntrFuxsvf802S09OrUJQByBnAu+QzJAUoDRL1DAb4eSJqcp+QEhaQInIRvk4QAAAABJRU5ErkJg",
            "gg==",
        ]
        data = dict(
            category="app",
            license_type="free",
            title="Testowa propozycja aplikacji",
            notes="Nieszczególnie\nciekawy\nopis",
            applicant_email="anyone@anywhere.any",
            author="Jan Kowalski",
            url="http://www.anywhere.any",
            datasets=[ds.id for ds in datasets[:2]],
            image="".join(image_b64),
            mobile_apple_url="https://example.com/apple",
            mobile_google_url="https://example.com/google",
            desktop_linux_url="https://example.com/linux",
            desktop_macos_url="https://example.com/macos",
            desktop_windows_url="https://example.com/windows",
        )
        obj = ShowcaseProposal.create(data)
        run_on_commit_events()
        assert obj.is_app
        assert not obj.is_other
        mail_filename = sorted(os.listdir(settings.EMAIL_FILE_PATH))[-1]
        last_mail_path = f"{settings.EMAIL_FILE_PATH}/{mail_filename}"
        with open(last_mail_path, "r") as mail_file:
            mail = mail_file.read()

            plain_begin = mail.find(
                'Content-Type: text/plain; charset="utf-8"\nMIME-Version: 1.0\n' "Content-Transfer-Encoding: 8bit"
            )
            html_begin = mail.find(
                'Content-Type: text/html; charset="utf-8"\nMIME-Version: 1.0\n' "Content-Transfer-Encoding: 8bit"
            )
            image_begin = mail.find("Content-Type: image/png\nMIME-Version: 1.0\n" "Content-Transfer-Encoding: base64")

            plain = mail[plain_begin:html_begin]
            html = mail[html_begin:image_begin]

            for key in (
                "applicant_email",
                "author",
                "desktop_linux_url",
                "desktop_macos_url",
                "desktop_windows_url",
                "mobile_apple_url",
                "mobile_google_url",
                "title",
                "url",
            ):
                assert data[key] in plain
                assert data[key] in html

            with override("pl"):
                for ds in datasets[:2]:
                    assert "pl" in ds.frontend_absolute_url
                    assert ds.frontend_absolute_url in plain, plain
                    assert ds.frontend_absolute_url in html, html

            assert data["notes"] in plain
            assert data["notes"].replace("\n", "<br>") in html
            assert "Darmowa aplikacja" in plain
            assert "Darmowa aplikacja" in html
