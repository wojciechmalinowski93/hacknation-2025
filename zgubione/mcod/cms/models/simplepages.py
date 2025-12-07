from django.db.models import TextField
from wagtail.admin.edit_handlers import FieldPanel, MultiFieldPanel, PublishingPanel
from wagtail.api import APIField
from wagtail.core.fields import RichTextField

from mcod.cms.api import fields
from mcod.cms.models.base import BasePage


class SimplePageIndex(BasePage):
    parent_page_types = ["cms.RootPage"]
    subpage_types = ["cms.SimplePage", "cms.ExtraSimplePage"]

    max_count = 1
    fixed_slug = "page"
    fixed_url_path = "page/"

    class Meta:
        verbose_name = "Lista prostych stron WWW"
        verbose_name_plural = "Listy prostych stron WWW"


class SimplePageMixin(BasePage):

    parent_page_types = [
        "cms.SimplePageIndex",
    ]

    subpage_types = []

    i18n_fields = BasePage.i18n_fields + [
        "body",
    ]

    api_fields = BasePage.api_fields + [APIField("body", serializer=fields.RichTextField(source="body_i18n"))]

    content_panels_pl = BasePage.content_panels + [
        FieldPanel("body", classname="full", heading="Treść strony"),
    ]

    content_panels_en = BasePage.content_panels_en + [
        FieldPanel("body_en", classname="full", heading="Treść strony"),
    ]

    settings_panels = [
        PublishingPanel(),
        MultiFieldPanel(
            [
                FieldPanel("slug"),
                FieldPanel("show_in_menus"),
            ],
            "Ustawienia strony",
        ),
    ]

    class Meta(BasePage.Meta):
        verbose_name = "Prosta strona WWW"
        verbose_name_plural = "Proste strony WWW"
        abstract = True

    def get_copyable_fields(self):
        return super().get_copyable_fields() + ["body"]


class SimplePage(SimplePageMixin):
    body = RichTextField(blank=True)
    body_en = RichTextField(blank=True, null=True)

    class Meta(SimplePageMixin.Meta):
        pass


class ExtraSimplePage(SimplePageMixin):
    body = TextField(blank=True)
    body_en = TextField(blank=True, null=True)

    max_count = 1

    class Meta(SimplePage.Meta):
        verbose_name = "Deklaracja dostępności"
        verbose_name_plural = "Deklaracje dostępności"
