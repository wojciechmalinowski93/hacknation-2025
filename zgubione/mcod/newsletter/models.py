import logging

import magic
from bs4 import BeautifulSoup
from constance import config
from django.contrib.auth.hashers import get_hasher
from django.core.exceptions import ValidationError
from django.db import models
from django.template.loader import render_to_string
from django.utils.timezone import now
from django.utils.translation import get_language, gettext_lazy as _, override

from mcod import settings
from mcod.core import storages
from mcod.core.db.models import TimeStampedModel
from mcod.lib.model_sanitization import SanitizedCharField, SanitizedTextField
from mcod.newsletter.tasks import (
    remove_inactive_subscription,
    send_newsletter_mail,
    send_subscription_confirm_mail,
)
from mcod.newsletter.utils import make_activation_code

logger = logging.getLogger("mcod")


class Subscription(TimeStampedModel):
    NEWSLETTER_LANGUAGES = (
        ("pl", _("polish")),
        ("en", _("english")),
    )
    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="newsletter_subscriptions",
        verbose_name=_("user"),
    )
    lang = models.CharField(max_length=7, choices=NEWSLETTER_LANGUAGES, verbose_name=_("language"))
    email = models.EmailField(verbose_name=_("email"), unique=True)
    activation_code = SanitizedCharField(verbose_name=_("activation code"), max_length=40, default=make_activation_code)
    is_active = models.BooleanField(default=False, verbose_name=_("is active?"), db_index=True)
    is_personal_data_processing_accepted = models.BooleanField(
        default=False,
        verbose_name=_("is personal data processing accepted?"),
    )
    is_personal_data_use_confirmed = models.BooleanField(
        default=False,
        verbose_name=_("is personal data gathering accepted?"),
    )
    subscribe_date = models.DateTimeField(verbose_name=_("subscribe date"), null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        models.DO_NOTHING,
        blank=True,
        null=True,
        verbose_name=_("created by"),
        related_name="newsletter_subscriptions_created",
    )
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        models.DO_NOTHING,
        blank=True,
        null=True,
        verbose_name=_("modified by"),
        related_name="newsletter_subscriptions_modified",
    )

    class Meta:
        verbose_name = _("subscription")
        verbose_name_plural = _("subscriptions")

    def __str__(self):
        return self.email

    def clean(self):
        super().clean()
        errors_dict = {}
        if not self.is_personal_data_processing_accepted:
            errors_dict.update({"is_personal_data_processing_accepted": _("This field is required!")})
        if not self.is_personal_data_use_confirmed:
            errors_dict.update({"is_personal_data_use_confirmed": _("This field is required!")})
        if errors_dict:
            raise ValidationError(errors_dict)

    @property
    def info(self):
        if self.is_active:
            return _("The newsletter subscription is active.")
        else:
            msg = _('You will receive an activation link to the e-mail address "%(email)s".')
            return msg % {"email": self.email}

    @classmethod
    def is_enabled(cls, email):
        return cls.objects.filter(email=email, is_active=True).exists()

    @classmethod
    def is_disabled(cls, email):
        return not cls.is_enabled(email)

    @classmethod
    def awaits_for_confirm(cls, email):
        return cls.objects.filter(email=email, is_active=False).exists()

    @classmethod
    def make_email_hash(cls, email):
        hasher = get_hasher()
        return hasher.encode(email, hasher.salt())

    @classmethod
    def subscribe(cls, email, user=None):
        defaults = {
            "user": user,
            "is_active": False,
            "is_personal_data_processing_accepted": True,
            "is_personal_data_use_confirmed": True,
            "lang": get_language(),
            "subscribe_date": None,
        }
        obj, created = cls.objects.update_or_create(email=email, defaults=defaults)
        logger.debug("Subscribing subscription %s.", obj)
        send_subscription_confirm_mail.s(obj.id).apply_async()
        remove_inactive_subscription.s(obj.id).apply_async(countdown=settings.NEWSLETTER_REMOVE_INACTIVE_TIMEOUT)
        return obj

    @property
    def api_resign_newsletter_url(self):
        return "/auth/newsletter/unsubscribe"

    @property
    def api_resign_newsletter_absolute_url(self):
        return f"{settings.API_URL}{self.api_resign_newsletter_url}"

    @property
    def api_subscribe_confirm_url(self):
        return f"/auth/newsletter/subscribe/{self.activation_code}/confirm"

    @property
    def api_subscribe_confirm_absolute_url(self):
        return f"{settings.API_URL}{self.api_subscribe_confirm_url}"

    @property
    def resign_newsletter_url(self):
        return f"/newsletter/unsubscribe/{self.activation_code}"

    @property
    def resign_newsletter_absolute_url(self):
        return f"{settings.BASE_URL}/{self.lang}{self.resign_newsletter_url}"

    @property
    def subscribe_confirm_url(self):
        return f"/newsletter/subscribe/{self.activation_code}"

    @property
    def subscribe_confirm_absolute_url(self):
        return f"{settings.BASE_URL}/{self.lang}{self.subscribe_confirm_url}"

    def confirm_subscription(self):
        self.is_active = True
        self.subscribe_date = now()
        self.save()

    def send_subscription_confirm_mail(self):
        with override(self.lang):
            subject = _("Activating the newsletter of dane.gov.pl portal")
            context = {
                "host": settings.BASE_URL,
                "url": self.subscribe_confirm_absolute_url,
            }
            message = render_to_string("newsletter/confirm_subscription.txt", context=context)
            html_message = render_to_string("newsletter/confirm_subscription.html", context=context)
            return self.send_mail(
                subject,
                message,
                config.NEWSLETTER_EMAIL,
                [
                    self.email,
                ],
                html_message=html_message,
            )

    def unsubscribe(self):
        logger.debug("Unsubscribing subscription %s.", self)
        _id = self.id
        self.delete()
        setattr(self, "id", _id)  # required by response serializer.
        return self


class NewsletterQuerySet(models.QuerySet):
    def to_send_today(self):
        return self.filter(planned_sending_date=now().date()).exclude(status="sent")


class Newsletter(TimeStampedModel):
    NEWSLETTER_LANGUAGES = (
        ("pl", _("polish")),
        ("en", _("english")),
    )
    NEWSLETTER_STATUS_CHOICES = (
        ("awaits", _("Awaits")),
        ("sent", _("Sent")),
        ("error", _("Error")),
    )
    title = SanitizedCharField(max_length=255, verbose_name=_("title"))
    lang = models.CharField(max_length=7, choices=NEWSLETTER_LANGUAGES, verbose_name=_("language version"))
    planned_sending_date = models.DateField(verbose_name=_("planned sending date"))
    sending_date = models.DateTimeField(verbose_name=_("sending date"), null=True, blank=True)
    status = models.CharField(
        max_length=7,
        choices=NEWSLETTER_STATUS_CHOICES,
        verbose_name=_("status"),
        default=NEWSLETTER_STATUS_CHOICES[0][0],
    )
    file = models.FileField(
        verbose_name=_("file"),
        storage=storages.get_storage("newsletter"),
        upload_to="%Y%m%d",
        max_length=2000,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        models.DO_NOTHING,
        verbose_name=_("created by"),
        related_name="newsletters_created",
    )
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        models.DO_NOTHING,
        blank=True,
        null=True,
        verbose_name=_("modified by"),
        related_name="newsletters_modified",
    )

    objects = NewsletterQuerySet.as_manager()

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = _("newsletter")
        verbose_name_plural = _("newsletters")
        db_table = "newsletter"

    @property
    def is_sent(self):
        return self.status == "sent"

    def clean_fields(self, exclude=None):
        super().clean_fields(exclude=exclude)
        if not self.lang:
            self.lang = get_language()
        if not self.is_sent and self.planned_sending_date and self.planned_sending_date <= now().date():
            if exclude and "planned_sending_date" in exclude:
                raise ValidationError(_("Planned sending date must be in future!"))
            else:
                raise ValidationError({"planned_sending_date": _("This date must be in future!")})

    @staticmethod
    def _get_required_links(html):
        soup = BeautifulSoup(html, "html.parser")
        required_links = soup.findAll("a", text="Rezygnacja")
        required_links += soup.findAll("a", text="Resignation")
        return required_links

    def clean(self):
        errors = {}
        if self.file:
            buffer = self.file.read()
            file_mime_type = magic.from_buffer(buffer, mime=True)
            if file_mime_type != "text/html":
                errors["file"] = _("This is not html file!")
            else:
                try:
                    html = buffer.decode("utf8")
                except UnicodeDecodeError:
                    html = buffer.decode("cp1250")
                required_links = self._get_required_links(html)
                if not required_links:
                    errors["file"] = _('Resignation link in html is required <a href="#">Resign</a>!')
        if errors:
            raise ValidationError(errors)

    def send(self):
        with open(self.file.path, "r") as f:
            html_template = f.read()
            required_links = [str(x) for x in self._get_required_links(html_template)]
            for obj in Subscription.objects.filter(is_active=True):
                html_message = str(html_template)
                for link in required_links:
                    updated_link = link.replace(
                        'href="#"',
                        'href="{}"'.format(obj.resign_newsletter_absolute_url),
                    )
                    html_message = html_message.replace(link, updated_link)
                send_newsletter_mail.s(self.id, obj.id, html_message).apply_async_on_commit()
        self.sending_date = now()
        self.status = "sent"
        self.save()


class Submission(TimeStampedModel):
    newsletter = models.ForeignKey(
        Newsletter,
        verbose_name=_("newsletter"),
        related_name="newsletter_submissions",
        on_delete=models.CASCADE,
    )
    subscription = models.ForeignKey(
        Subscription,
        verbose_name=_("subscription"),
        related_name="subscription_submissions",
        on_delete=models.CASCADE,
    )
    message = SanitizedTextField(verbose_name=_("message"), blank=True)

    class Meta:
        verbose_name = _("submission")
        verbose_name_plural = _("submissions")
        unique_together = ("newsletter", "subscription")

    def __str__(self):
        return "{} - {}".format(self.newsletter.title, self.subscription.email)

    @property
    def title(self):
        return self.__str__()

    def send_newsletter_mail(self, html_message):
        self.send_mail(
            self.newsletter.title,
            "",
            config.NEWSLETTER_EMAIL,
            [self.subscription.email],
            html_message=html_message,
        )
