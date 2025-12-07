import os
from io import BytesIO

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.forms.models import model_to_dict
from django.templatetags.static import static
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _, pgettext_lazy
from model_utils import FieldTracker
from modeltrans.fields import TranslationField
from PIL import Image

from mcod import settings
from mcod.core import signals as core_signals, storages
from mcod.core.api.search import signals as search_signals
from mcod.core.db.models import ExtendedModel, TrashModelBase
from mcod.lib.model_sanitization import (
    SanitizedCharField,
    SanitizedJSONField,
    SanitizedTextField,
    SanitizedTranslationField,
)
from mcod.showcases.managers import (
    ShowcaseManager,
    ShowcaseProposalManager,
    ShowcaseProposalTrashManager,
    ShowcaseTrashManager,
)
from mcod.showcases.signals import generate_thumbnail, update_showcase_document
from mcod.showcases.tasks import generate_logo_thumbnail_task, send_showcase_proposal_mail_task

User = get_user_model()


class ShowcaseMixin(ExtendedModel):
    APPLICATION_PLATFORMS = {
        "apple": "iOS",
        "google": "Android",
        "linux": "Linux",
        "macos": "MacOS",
        "windows": "Windows",
    }
    APPLICATION_TYPES_PLURAL = {
        "mobile": _("Mobile Applications"),
        "desktop": _("Desktop Applications"),
    }
    CATEGORY_CHOICES = (
        ("app", _("Application")),
        ("www", pgettext_lazy("showcase category name", "Website")),
        ("other", _("Other")),
    )
    CATEGORY_NAMES = dict(CATEGORY_CHOICES)
    CATEGORIES = [code for code, _ in CATEGORY_CHOICES]
    LICENSE_TYPE_CHOICES = (
        ("free", _("Free App")),
        ("commercial", _("Commercial App")),
    )
    LICENSE_TYPE_NAMES = {
        "free": pgettext_lazy("license type", "Free"),
        "commercial": pgettext_lazy("license type", "Commercial"),
    }
    LICENSE_TYPES = [code for code, _ in LICENSE_TYPE_CHOICES]

    category = models.CharField(max_length=5, verbose_name=_("category"), choices=CATEGORY_CHOICES)
    title = SanitizedCharField(max_length=300, verbose_name=_("title"))
    notes = SanitizedTextField(verbose_name=_("Notes"), null=True)
    author = SanitizedCharField(max_length=50, blank=True, null=True, verbose_name=_("Author"))
    url = models.URLField(max_length=300, verbose_name=_("App URL"), null=True)
    external_datasets = SanitizedJSONField(blank=True, null=True, default=list, verbose_name=_("external datasets"))
    is_mobile_app = models.BooleanField(default=False, verbose_name=_("is mobile app?"))
    is_desktop_app = models.BooleanField(default=False, verbose_name=_("is desktop app?"))
    mobile_apple_url = models.URLField(verbose_name=_("Apple Store URL"), blank=True)
    mobile_google_url = models.URLField(verbose_name=_("Google Store URL"), blank=True)
    desktop_linux_url = models.URLField(verbose_name=_("Linux App URL"), blank=True)
    desktop_macos_url = models.URLField(verbose_name=_("MacOS App URL"), blank=True)
    desktop_windows_url = models.URLField(verbose_name=_("Windows App URL"), blank=True)
    license_type = models.CharField(
        max_length=10,
        blank=True,
        choices=LICENSE_TYPE_CHOICES,
        verbose_name=_("license type"),
    )

    def __str__(self):
        return self.title

    class Meta(ExtendedModel.Meta):
        default_manager_name = "objects"
        abstract = True

    @property
    def app_info(self):
        is_mobile = "{}<br>".format(_("Mobile Application")) if self.is_mobile_app else ""
        mobile = "{}{}{}<br>".format(
            is_mobile,
            self._get_url_info(self.mobile_apple_url, "ic-apple.svg", "iOS"),
            self._get_url_info(self.mobile_google_url, "ic-android.svg", "Android"),
        )

        is_desktop = "{}<br>".format(_("Desktop Application")) if self.is_desktop_app else ""
        desktop = "{}{}{}{}<br>".format(
            is_desktop,
            self._get_url_info(self.desktop_windows_url, "ic-windows.svg", "Windows"),
            self._get_url_info(self.desktop_linux_url, "ic-linux.svg", "Linux"),
            self._get_url_info(self.desktop_macos_url, "ic-apple.svg", "MacOS"),
        )
        return self.mark_safe(f"{mobile}{desktop}")

    @property
    def category_name(self):
        return self.get_category_display()

    @property
    def showcase_category(self):
        return self.category

    @property
    def showcase_types(self):
        result = []
        if self.is_mobile_app:
            result.append("mobile")
        if self.is_desktop_app:
            result.append("desktop")
        return result

    @property
    def showcase_platforms(self):
        result = []
        if self.mobile_apple_url:
            result.append("apple")
        if self.mobile_google_url:
            result.append("google")
        if self.desktop_linux_url:
            result.append("linux")
        if self.desktop_macos_url:
            result.append("macos")
        if self.desktop_windows_url:
            result.append("windows")
        return result

    @property
    def illustrative_graphics_url(self):
        return self._get_absolute_url(self.illustrative_graphics.url, use_lang=False) if self.illustrative_graphics else None

    @property
    def illustrative_graphics_img(self):
        url = self.illustrative_graphics_url
        alt = getattr(self, "illustrative_graphics_alt", "")
        if url:
            return self.mark_safe(
                f'<a href="{self.admin_change_url}" target="_blank"><img src="{url}" width="100" alt="{alt}" /></a>'
            )

    @property
    def is_app(self):
        return self.category == "app"

    @property
    def is_www(self):
        return self.category == "www"

    @property
    def is_other(self):
        return self.category == "other"

    def _get_url_info(self, url, icon, name):
        if url:
            icon = static(f"/showcases/icons/{icon}")
            text = _("link to the application")
            return f'<img src="{icon}" alt="logo" /> {name} - {text}: <a href="{url}">{url}</a><br>'
        return ""

    def save_file(self, content, filename, field_name="image"):
        dt = self.created.date() if self.created else timezone.now().date()
        subdir = os.path.join(field_name, dt.isoformat().replace("-", ""))
        field = getattr(self, field_name)
        dest_dir = os.path.join(field.storage.location, subdir)
        os.makedirs(dest_dir, exist_ok=True)
        file_path = os.path.join(dest_dir, filename)
        with open(file_path, "wb") as f:
            f.write(content.read())
        return "%s/%s" % (subdir, filename)


class ShowcaseProposal(ShowcaseMixin):
    DECISION_CHOICES = (
        ("accepted", _("Proposal accepted")),
        ("rejected", _("Proposal rejected")),
    )
    applicant_email = models.EmailField(verbose_name=_("applicant email"), blank=True)
    image = models.ImageField(
        max_length=200,
        storage=storages.get_storage("showcases"),
        upload_to="proposals/image/%Y%m%d",
        blank=True,
        null=True,
        verbose_name=_("image URL"),
    )
    illustrative_graphics = models.ImageField(
        max_length=200,
        storage=storages.get_storage("showcases"),
        upload_to="proposals/illustrative_graphics/%Y%m%d",
        blank=True,
        null=True,
        verbose_name=_("illustrative graphics"),
    )
    datasets = models.ManyToManyField(
        "datasets.Dataset",
        blank=True,
        verbose_name=_("datasets"),
        related_name="showcase_proposals",
    )
    keywords = ArrayField(SanitizedCharField(max_length=100), verbose_name=_("keywords"), default=list)
    report_date = models.DateField(verbose_name=_("report date"))
    decision = models.CharField(max_length=8, verbose_name=_("decision"), choices=DECISION_CHOICES, blank=True)
    decision_date = models.DateField(verbose_name=_("decision date"), null=True, blank=True)
    comment = SanitizedTextField(verbose_name=_("comment"), blank=True)

    showcase = models.OneToOneField(
        "showcases.Showcase",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("showcase"),
    )
    created_by = models.ForeignKey(
        User,
        models.DO_NOTHING,
        blank=True,
        null=True,
        verbose_name=_("created by"),
        related_name="showcase_proposals_created",
    )

    modified_by = models.ForeignKey(
        User,
        models.DO_NOTHING,
        blank=True,
        null=True,
        verbose_name=_("modified by"),
        related_name="showcase_proposals_modified",
    )

    objects = ShowcaseProposalManager()
    trash = ShowcaseProposalTrashManager()
    i18n = TranslationField()
    tracker = FieldTracker()

    class Meta(ShowcaseMixin.Meta):
        verbose_name = _("Showcase Proposal")
        verbose_name_plural = _("Showcase Proposals")

    @property
    def application_logo(self):
        return (
            self.mark_safe(
                '<a href="%s" target="_blank"><img src="%s" width="%d" alt="" /></a>'
                % (
                    self.admin_change_url,
                    self.image_absolute_url,
                    100,
                )
            )
            if self.image_absolute_url
            else ""
        )

    @property
    def applicant_email_link(self):
        if self.applicant_email:
            return self.mark_safe(f'<a href="mailto:{self.applicant_email}">{self.applicant_email}</a>')

    @property
    def datasets_ids_as_str(self):
        return ",".join(str(x.id) for x in self.datasets.order_by("id"))

    @property
    def datasets_links(self):
        queryset = self.datasets.order_by("title")
        res = "<br>".join([f'<a href="{x.frontend_absolute_url}" target="_blank">{x.title}</a>' for x in queryset])
        return self.mark_safe(res)

    @property
    def datasets_links_info(self):
        res = "\n".join([obj.frontend_absolute_url for obj in self.datasets.order_by("title")])
        return self.mark_safe(res)

    @property
    def external_datasets_links(self):
        data = [[x.get("url"), x.get("title") or x.get("url")] for x in self.external_datasets]
        return self.mark_safe("<br>".join([f'<a href="{x[0]}" target="_blank">{x[1]}</a>' for x in data]))

    @property
    def external_datasets_info(self):
        data = [[x.get("title") or x.get("url"), x.get("url")] for x in self.external_datasets]
        return self.mark_safe("".join([f"{x[0]}: {x[1]}\n" for x in data]))

    @cached_property
    def image_absolute_url(self):
        return self._get_absolute_url(self.image.url, use_lang=False) if self.image else ""

    @property
    def is_accepted(self):
        return self.decision == "accepted"

    @property
    def is_converted_to_showcase(self):
        return self.showcase and not self.showcase.is_permanently_removed

    @property
    def is_rejected(self):
        return self.decision == "rejected"

    @property
    def keywords_as_str(self):
        return ",".join([x for x in self.keywords])

    @classmethod
    def accusative_case(cls):
        return _("acc: showcase proposal")

    def convert_to_showcase(self):  # noqa
        created = False
        if self.is_converted_to_showcase:
            return created  # proposal is after convertion already. Do not convert.
        tag_model = apps.get_model("tags.Tag")
        data = model_to_dict(
            self,
            fields=[
                "category",
                "notes",
                "author",
                "url",
                "title",
                "image",
                "illustrative_graphics",
                "datasets",
                "external_datasets",
                "keywords",
                "created_by",
                "modified_by",
                "is_mobile_app",
                "is_desktop_app",
                "mobile_apple_url",
                "mobile_google_url",
                "desktop_windows_url",
                "desktop_linux_url",
                "desktop_macos_url",
                "license_type",
            ],
        )
        data["status"] = "draft"
        data["modified_by_id"] = data.pop("modified_by")
        data["created_by_id"] = data.pop("created_by") or data["modified_by_id"]
        image = data.pop("image")
        illustrative_graphics = data.pop("illustrative_graphics")
        datasets = data.pop("datasets")
        keywords = data.pop("keywords", [])
        showcase = Showcase.objects.create(**data)
        if image:
            showcase.image = showcase.save_file(image, os.path.basename(image.path))
        if illustrative_graphics:
            showcase.illustrative_graphics = showcase.save_file(
                illustrative_graphics,
                os.path.basename(illustrative_graphics.path),
                field_name="illustrative_graphics",
            )
        if image or illustrative_graphics:
            showcase.save()
        if datasets:
            showcase.datasets.set(datasets)
        tag_ids = []
        for name in keywords:
            tag, created = tag_model.objects.get_or_create(
                name=name,
                language="pl",
                defaults={"created_by_id": data["created_by_id"]},
            )
            tag_ids.append(tag.id)
        if tag_ids:
            showcase.tags.set(tag_ids)
        self.showcase = showcase
        self.save()
        created = True
        return created

    @classmethod
    def create(cls, data):
        image = data.pop("image", None)
        illustrative_graphics = data.pop("illustrative_graphics", None)
        datasets_ids = data.pop("datasets", [])
        name = cls.slugify(data["title"])
        if image:
            data["image"] = cls.decode_b64_image(image, name)
        if illustrative_graphics:
            data["illustrative_graphics"] = cls.decode_b64_image(illustrative_graphics, name)
        obj = cls.objects.create(**data)
        if datasets_ids:
            obj.datasets.set(datasets_ids)
        send_showcase_proposal_mail_task.s(obj.id).apply_async_on_commit()
        return obj

    @classmethod
    def send_showcase_proposal_mail(cls, obj):
        cls.send_mail_message(
            "Powiadomienie - Nowe zgłoszenie PoCoTo",
            {"obj": obj},
            "mails/showcaseproposal.txt",
            "mails/showcaseproposal.html",
        )


class ShowcaseProposalTrash(ShowcaseProposal, metaclass=TrashModelBase):
    class Meta(ShowcaseProposal.Meta):
        proxy = True
        verbose_name = _("Showcase Proposal Trash")
        verbose_name_plural = _("Showcase Proposals Trash")


class Showcase(ShowcaseMixin):
    MAIN_PAGE_ORDERING_CHOICES = [
        (1, _("First")),
        (2, _("Second")),
        (3, _("Third")),
        (4, _("Fourth")),
    ]
    SIGNALS_MAP = {
        "updated": (generate_thumbnail, core_signals.notify_updated),
        "published": (generate_thumbnail, core_signals.notify_published),
        "restored": (
            search_signals.update_document_with_related,
            generate_thumbnail,
            core_signals.notify_restored,
        ),
        "removed": (
            search_signals.remove_document_with_related,
            core_signals.notify_removed,
        ),
        "pre_m2m_added": (core_signals.notify_m2m_added,),
        "pre_m2m_removed": (core_signals.notify_m2m_removed,),
        "pre_m2m_cleaned": (core_signals.notify_m2m_cleaned,),
        "post_m2m_added": (
            update_showcase_document,
            search_signals.update_document_related,
        ),
        "post_m2m_removed": (
            update_showcase_document,
            search_signals.update_document_related,
        ),
        "post_m2m_cleaned": (
            update_showcase_document,
            search_signals.update_document_related,
        ),
    }

    image = models.ImageField(
        max_length=200,
        storage=storages.get_storage("showcases"),
        upload_to="image/%Y%m%d",
        blank=True,
        null=True,
        verbose_name=_("Image URL"),
    )
    illustrative_graphics = models.ImageField(
        max_length=200,
        storage=storages.get_storage("showcases"),
        upload_to="illustrative_graphics/%Y%m%d",
        blank=True,
        null=True,
        verbose_name=_("illustrative graphics"),
    )
    illustrative_graphics_alt = SanitizedCharField(
        max_length=255,
        blank=True,
        verbose_name=_("illustrative graphics alternative text"),
    )
    image_thumb = models.ImageField(
        storage=storages.get_storage("showcases"),
        upload_to="image_thumb/%Y%m%d",
        blank=True,
        null=True,
    )
    image_alt = SanitizedCharField(max_length=255, null=True, blank=True, verbose_name=_("Alternative text"))
    datasets = models.ManyToManyField(
        "datasets.Dataset",
        db_table="showcase_dataset",
        verbose_name=_("Datasets"),
        related_name="showcases",
        related_query_name="showcase",
    )
    tags = models.ManyToManyField(
        "tags.Tag",
        blank=True,
        db_table="showcase_tag",
        verbose_name=_("Tag"),
        related_name="showcases",
        related_query_name="showcase",
    )

    main_page_position = models.PositiveSmallIntegerField(
        choices=MAIN_PAGE_ORDERING_CHOICES,
        blank=True,
        null=True,
        unique=True,
        verbose_name=_("Positioning on the main page"),
    )
    created_by = models.ForeignKey(
        User,
        models.DO_NOTHING,
        blank=False,
        editable=False,
        null=True,
        verbose_name=_("Created by"),
        related_name="showcases_created",
    )
    modified_by = models.ForeignKey(
        User,
        models.DO_NOTHING,
        blank=False,
        editable=False,
        null=True,
        verbose_name=_("Modified by"),
        related_name="showcases_modified",
    )
    i18n = SanitizedTranslationField(fields=("title", "notes", "image_alt", "illustrative_graphics_alt"))

    objects = ShowcaseManager()
    trash = ShowcaseTrashManager()

    tracker = FieldTracker()
    slugify_field = "title"

    class Meta(ShowcaseMixin.Meta):
        verbose_name = _("Showcase")
        verbose_name_plural = _("Showcases")
        db_table = "showcase"
        indexes = [
            GinIndex(fields=["i18n"]),
        ]

    @property
    def frontend_preview_url(self):
        return self._get_absolute_url(f"/showcase/preview/{self.ident}")

    @cached_property
    def image_url(self):
        url = self.image.url if self.image else ""
        if url:
            return self._get_absolute_url(url, use_lang=False)
        return url

    @cached_property
    def image_absolute_url(self):
        return self._get_absolute_url(self.image.url, use_lang=False) if self.image else ""

    @cached_property
    def image_thumb_url(self):
        url = self.image_thumb.url if self.image_thumb else ""
        if url:
            return self._get_absolute_url(url, use_lang=False)
        return url

    @cached_property
    def image_thumb_absolute_url(self):
        return self._get_absolute_url(self.image_thumb.url, use_lang=False) if self.image_thumb else ""

    @cached_property
    def has_image_thumb(self):
        return bool(self.image_thumb)

    def tags_as_str(self, lang):
        return ", ".join(sorted([tag.name for tag in self.tags.filter(language=lang)], key=str.lower))

    @property
    def keywords_list(self):
        return [tag.to_dict for tag in self.tags.all()]

    @property
    def keywords(self):
        return self.tags

    @property
    def preview_link(self):
        return self.mark_safe(f'<a href="{self.frontend_preview_url}" class="btn" target="_blank">{_("Preview")}</a>')

    @property
    def application_logo(self):
        if self.image_thumb_absolute_url or self.image_absolute_url:
            return self.mark_safe(
                '<a href="%s" target="_blank"><img src="%s" width="%d" alt="%s" /></a>'
                % (
                    self.admin_change_url,
                    self.image_thumb_absolute_url or self.image_absolute_url,
                    100,
                    (self.image_alt if self.image_alt else f"Logo aplikacji {self.title}"),
                )
            )
        return ""

    @classmethod
    def accusative_case(cls):
        return _("acc: Showcase")

    def published_datasets(self):
        return self.datasets.filter(status="published")

    def generate_logo_thumbnail(self):
        if not self.image:
            self.image_thumb = None
        else:
            image = Image.open(self.image)
            image = image.convert("RGB") if image.mode not in ("L", "RGB", "RGBA") else image
            image.thumbnail(settings.THUMB_SIZE, Image.ANTIALIAS)

            temp_handle = BytesIO()
            image.save(temp_handle, "png")
            temp_handle.seek(0)

            suf = SimpleUploadedFile(
                os.path.split(self.image.name)[-1],
                temp_handle.read(),
                content_type="image/png",
            )
            thumb_name = ".".join(suf.name.split(".")[:-1]) + "_thumb.png"
            self.image_thumb.save(thumb_name, suf, save=False)


class ShowcaseTrash(Showcase, metaclass=TrashModelBase):
    class Meta(Showcase.Meta):
        proxy = True
        verbose_name = _("Showcase Trash")
        verbose_name_plural = _("Showcases Trash")


@receiver(pre_save, sender=ShowcaseProposal)
def handle_showcase_proposal_pre_save(sender, instance, *args, **kwargs):
    if not instance.report_date and instance.created:
        instance.report_date = instance.created.date()
    if instance.tracker.has_changed("decision"):
        instance.decision_date = timezone.now().date() if any([instance.is_accepted, instance.is_rejected]) else None


@receiver(generate_thumbnail, sender=Showcase)
def regenerate_thumbnail(sender, instance, *args, **kwargs):
    sender.log_debug(instance, "Regenerating thumbnail ", "generate_thumbnail")
    if any(
        [
            instance.tracker.has_changed("image"),
            instance.tracker.has_changed("status") and instance.status == instance.STATUS.published,
        ]
    ):
        generate_logo_thumbnail_task.s(instance.id).apply_async_on_commit()
    else:
        search_signals.update_document.send(sender, instance)


@receiver(update_showcase_document, sender=Showcase)
def update_showcase_document_handler(sender, instance, *args, **kwargs):
    if instance.status == instance.STATUS.published:
        search_signals.update_document.send(sender, instance, *args, **kwargs)


@receiver(pre_save, sender=Showcase)
def handle_showcase_pre_save(sender, instance, *args, **kwargs):
    if instance.is_removed and instance.main_page_position is not None:
        instance.main_page_position = None
