import logging
from functools import partial
from urllib.parse import urlencode, urljoin

from django.db import models
from django.shortcuts import redirect
from django.utils.text import slugify
from django.utils.translation import activate, get_language, gettext_lazy as _
from fancy_cache.memory import find_urls
from modeltrans.fields import TranslationField
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.fields import CharField
from wagtail.admin.edit_handlers import FieldPanel, MultiFieldPanel, ObjectList, TabbedInterface
from wagtail.api import APIField
from wagtail.core.models import Page, PageBase, PageLogEntry
from wagtail.core.utils import WAGTAIL_APPEND_SLASH
from wagtail.documents.models import AbstractDocument
from wagtail.images.models import AbstractImage, AbstractRendition

from mcod.cms.fields import CustomTextField
from mcod.core.api.search.signals import remove_document, update_document
from mcod.core.db.mixins import ApiMixin

logger = logging.getLogger("wagtail.core")
mcod_logger = logging.getLogger("mcod")


class BasePageMeta(PageBase):
    def __init__(self, name, bases, dct):
        super().__init__(name, bases, dct)

    @staticmethod
    def prepare_i18_field(inst, field=None):
        val = ""
        if field:
            lang = get_language()
            pl_val = getattr(inst, field)
            en_val = getattr(inst, "{}_en".format(field)) or pl_val
            val = pl_val if lang == "pl" else en_val
        return val

    @staticmethod
    def prepare_translated_field(instance, field=None):
        if field:
            attrs = {
                "pl": str(getattr(instance, field) or getattr(instance, f"{field}_i18n")),
                "en": str(getattr(instance, f"{field}_en") or getattr(instance, f"{field}_i18n")),
            }
            obj = type("{}_translated".format(field), (object,), attrs)

            return obj

    def __new__(cls, name, bases, attrs, **kwargs):
        klass = super().__new__(cls, name, bases, attrs, **kwargs)

        if "edit_handler" not in attrs:
            klass.edit_handler = TabbedInterface(
                [
                    ObjectList(klass.content_panels_pl, heading="Treść (PL)"),
                    ObjectList(klass.content_panels_en, heading="Treść (EN)"),
                    ObjectList(klass.seo_panels_pl, heading="Promocja (PL)"),
                    ObjectList(klass.seo_panels_en, heading="Promocja (EN)"),
                    ObjectList(
                        klass.settings_panels,
                        heading="Ustawienia",
                        classname="settings",
                    ),
                ]
            )

        i18n_fields = getattr(klass, "i18n_fields", [])

        for field in i18n_fields:
            f = partial(cls.prepare_i18_field, field=field)
            setattr(klass, "{}_i18n".format(field), property(f))
            f = partial(cls.prepare_translated_field, field=field)
            setattr(klass, "{}_translated".format(field), property(f))

        return klass


class BasePage(ApiMixin, Page, metaclass=BasePageMeta):
    title_en = models.CharField(
        verbose_name=_("title"),
        max_length=255,
        help_text=_("The page title as you'd like it to be seen by the public"),
        null=True,
        blank=True,
    )
    seo_title_en = models.CharField(
        verbose_name=_("page title"),
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Optional. 'Search Engine Friendly' title. This will appear at the top of the browser window."),
    )
    search_description_en = models.TextField(verbose_name=_("search description"), blank=True, null=True)
    draft_title_en = models.CharField(max_length=255, editable=False, null=True)
    indexable = False

    def get_copyable_fields(self):
        return ["title"]

    @property
    def is_indexable(self):
        return self.indexable or False

    @property
    def modified(self):
        return self.last_published_at

    @property
    def created(self):
        return self.first_published_at

    @property
    def status(self):
        return "published" if self.live else "draft"

    @property
    def slug_en(self):
        return self.slug

    fixed_slug = None
    fixed_url_path = None
    i18n_fields = ["title", "slug", "seo_title", "search_description"]

    content_panels_pl = [
        FieldPanel("title", classname="full title"),
    ]

    content_panels_en = [
        FieldPanel("title_en", classname="full title"),
    ]

    seo_panels_pl = [
        MultiFieldPanel(
            [
                FieldPanel("seo_title"),
                FieldPanel("search_description"),
            ],
            "Ustawienia SEO",
        ),
    ]
    seo_panels_en = [
        MultiFieldPanel(
            [
                FieldPanel("seo_title_en"),
                FieldPanel("search_description_en"),
            ],
            "Ustawienia SEO",
        ),
    ]
    settings_panels = [MultiFieldPanel([FieldPanel("show_in_menus")], "Ustawienia strony")]

    api_fields = [
        APIField("title", serializer=CharField(source="title_i18n")),
        APIField("slug", serializer=CharField(source="real_slug")),
        APIField("url_path"),
        APIField("seo_title", serializer=CharField(source="seo_title_i18n")),
        APIField("search_description", serializer=CharField(source="search_description_i18n")),
        APIField("first_published_at"),
        APIField("last_published_at"),
        APIField("latest_revision_created_at"),
    ]

    def full_clean(self, *args, **kwargs):
        base_slug = slugify(self.title) if not self.slug else slugify(self.slug)
        if base_slug:
            self.slug = self._get_autogenerated_slug(base_slug)

        if not self.draft_title:
            self.draft_title = self.title

        if not self.draft_title_en:
            self.draft_title_en = self.title_en

        super().full_clean(*args, **kwargs)

    def save_revision(
        self,
        user=None,
        submitted_for_moderation=False,
        approved_go_live_at=None,
        changed=True,
        log_action=False,
        previous_revision=None,
        clean=True,
    ):
        # Raise an error if this page is an alias.
        if self.alias_of_id:
            raise RuntimeError(
                "save_revision() was called on an alias page. "
                "Revisions are not required for alias pages as they are an exact copy of another page."
            )

        if clean:
            self.full_clean()

        # Create revision
        revision = self.revisions.create(
            content_json=self.to_json(),
            user=user,
            submitted_for_moderation=submitted_for_moderation,
            approved_go_live_at=approved_go_live_at,
        )

        update_fields = []

        self.latest_revision_created_at = revision.created_at
        update_fields.append("latest_revision_created_at")

        self.draft_title = self.title
        update_fields.append("draft_title")

        self.draft_title_en = self.title_en
        update_fields.append("draft_title_en")

        if changed:
            self.has_unpublished_changes = True
            update_fields.append("has_unpublished_changes")

        if update_fields:
            # clean=False because the fields we're updating don't need validation
            self.save(update_fields=update_fields, clean=False)

        # Log
        logger.info('Page edited: "%s" id=%d revision_id=%d', self.title, self.id, revision.id)
        if log_action:
            if not previous_revision:
                PageLogEntry.objects.log_action(
                    instance=self,
                    action=(log_action if isinstance(log_action, str) else "wagtail.edit"),
                    user=user,
                    revision=revision,
                    content_changed=changed,
                )
            else:
                PageLogEntry.objects.log_action(
                    instance=self,
                    action=(log_action if isinstance(log_action, str) else "wagtail.revert"),
                    user=user,
                    data={
                        "revision": {
                            "id": previous_revision.id,
                            "created": previous_revision.created_at.strftime("%d %b %Y %H:%M"),
                        }
                    },
                    revision=revision,
                    content_changed=changed,
                )

        if submitted_for_moderation:
            logger.info(
                'Page submitted for moderation: "%s" id=%d revision_id=%d',
                self.title,
                self.id,
                revision.id,
            )

        return revision

    def save_post(self, request):
        raise MethodNotAllowed(method="POST")

    def with_content_json(self, content_json):
        obj = self.specific_class.from_json(content_json)

        obj.pk = self.pk
        obj.content_type = self.content_type

        obj.path = self.path
        obj.depth = self.depth
        obj.numchild = self.numchild

        obj.set_url_path(self.get_parent())

        obj.draft_title = self.draft_title
        obj.draft_title_en = self.draft_title_en
        obj.live = self.live
        obj.has_unpublished_changes = self.has_unpublished_changes
        obj.owner = self.owner
        obj.locked = self.locked
        obj.locked_by = self.locked_by
        obj.locked_at = self.locked_at
        obj.latest_revision_created_at = self.latest_revision_created_at
        obj.first_published_at = self.first_published_at

        return obj

    @property
    def real_slug(self):
        return self.fixed_slug or self.slug

    def set_url_path(self, parent):
        _path = self.fixed_url_path

        if _path is None:
            _path = self.real_slug + "/"

        _path = parent.url_path + _path if parent else _path

        url_parts = [part.strip("/") for part in _path.split("/") if part]
        self.url_path = "/{}/".format("/".join(url_parts)).replace("//", "/")

        return self.url_path

    def get_url_parts(self, request=None, skip_root_path=True):
        possible_sites = [
            (pk, path, url, language_code)
            for pk, path, url, language_code in self._get_site_root_paths(request)
            if self.url_path.startswith(path)
        ]

        if not possible_sites:
            return None

        site_id, root_path, root_url, language_code = possible_sites[0]

        if hasattr(request, "site"):
            for site_id, root_path, root_url, language_code in possible_sites:
                if site_id == request.site.pk:
                    break
            else:
                site_id, root_path, root_url, language_code = possible_sites[0]

        if skip_root_path:
            page_path = self.url_path.replace(root_path, "/")

        if not WAGTAIL_APPEND_SLASH and page_path != "/":
            page_path = page_path.rstrip("/")

        return (site_id, root_url, page_path)

    def serve(self, request, *args, **kwargs):
        lang = get_language()
        activate(lang)
        is_preview = getattr(request, "is_preview", False)
        rev_id = getattr(request, "revision_id", -1)
        params = {"lang": lang}
        if is_preview and rev_id:
            params["rev"] = rev_id
        q = "?{}".format(urlencode(params))
        _url = urljoin(self.full_url, q)
        return redirect(_url)

    @staticmethod
    def clear_cache(instance, signal_name):
        if getattr(instance, "url_path", None):
            urls = [
                f"*{instance.url_path}",
                f"*{instance.url_path}?*",
            ]
            parent = instance.get_parent()
            if parent and getattr(parent, "url_path", None):
                urls += [
                    f"*{parent.url_path}",
                    f"*{parent.url_path}?*",
                ]
            removed_cache_items = list(find_urls(urls, purge=True))
            for url, key, count in removed_cache_items:
                mcod_logger.debug(
                    'URL "%s" removed from cache on %s "%s" page signal.',
                    url,
                    signal_name,
                    instance,
                )

    @staticmethod
    def on_post_save(sender, instance, **kwargs):
        if getattr(instance, "is_indexable", False):
            if instance.live:
                update_document.send(sender, instance)
        if hasattr(sender, "clear_cache"):
            sender.clear_cache(instance, "post_save")

    @staticmethod
    def on_pre_delete(sender, instance, using, **kwargs):
        if getattr(instance, "is_indexable", False):
            remove_document.send(sender, instance)

    @staticmethod
    def on_unpublish(sender, instance, **kwargs):
        if getattr(instance, "is_indexable", False):
            remove_document.send(sender, instance)

    @staticmethod
    def on_post_page_move(sender, instance, **kwargs):
        if hasattr(sender, "clear_cache"):
            sender.clear_cache(instance, "post_page_move")

    class Meta:
        abstract = True


class CustomDocument(AbstractDocument):
    admin_form_fields = ("title", "file", "collection")


class CustomImage(AbstractImage):
    alt = CustomTextField(
        max_length=150,
        blank=True,
        verbose_name=_("Alternative text"),
        help_text=_("Alternative text should be as descriptive and short as possible (max 150 chars)."),
    )

    i18n = TranslationField(fields=("alt",))

    admin_form_fields = (
        "title",
        "alt_pl",
        "alt_en",
        "file",
        "collection",
        "focal_point_x",
        "focal_point_y",
        "focal_point_width",
        "focal_point_height",
    )

    class Meta:
        verbose_name = _("image")
        verbose_name_plural = _("images")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        alt = self._meta.get_field("alt")
        self._meta.get_field("alt_pl")._help_text = alt.help_text
        self._meta.get_field("alt_en")._help_text = alt.help_text
        self._title = self.title

    @property
    def default_alt_text(self):
        return self.alt_i18n  # isn't working 100% as intended because EN and PL tabs don't provide lang query param in requests


class CustomRendition(AbstractRendition):
    image = models.ForeignKey(CustomImage, related_name="renditions", on_delete=models.CASCADE)

    class Meta:
        unique_together = (("image", "filter_spec", "focal_point_key"),)
