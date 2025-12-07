from wagtail.admin.edit_handlers import (
    FieldPanel,
    MultiFieldPanel,
    PublishingPanel,
    StreamFieldPanel,
)
from wagtail.api import APIField
from wagtail.api.v2.serializers import StreamField as StreamFieldSerializer
from wagtail.core.fields import StreamField

from mcod.cms.blocks.common import CarouselBlockWithAdditionalTextTools
from mcod.cms.models.base import BasePage


class ReportRootPage(BasePage):
    parent_page_types = ["cms.RootPage"]
    subpage_types = [
        "cms.BrokenLinksInfo",
    ]

    max_count = 1
    fixed_slug = "report"
    fixed_url_path = "report/"

    class Meta:
        verbose_name = "Raporty"
        verbose_name_plural = "Raporty"


class ReportAbstractSubpage(BasePage):

    body = StreamField(
        CarouselBlockWithAdditionalTextTools(required=False),
        default=None,
        blank=True,
        verbose_name="Tekst",
        help_text="Treść strony.",
    )

    body_en = StreamField(
        CarouselBlockWithAdditionalTextTools(required=False),
        default=None,
        blank=True,
        verbose_name="Tekst",
        help_text="Treść strony.",
    )

    api_fields = BasePage.api_fields + [
        APIField("body", serializer=StreamFieldSerializer(source="body_i18n")),
    ]

    content_panels_pl = BasePage.content_panels_pl + [
        StreamFieldPanel("body"),
    ]

    content_panels_en = BasePage.content_panels_en + [
        StreamFieldPanel("body_en"),
    ]

    i18n_fields = BasePage.i18n_fields + [
        "body",
    ]

    parent_page_types = [
        "cms.ReportRootPage",
    ]

    subpage_types = []

    indexable = True

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

    class Meta:
        abstract = True

    def get_copyable_fields(self):
        return super().get_copyable_fields() + ["body"]


class BrokenLinksInfo(ReportAbstractSubpage):
    max_count = 1
    fixed_slug = "brokenlinks-info"
    fixed_url_path = "brokenlinks-info/"

    class Meta:
        verbose_name = "Informacje o raporcie Uszkodzone linki"
        verbose_name_plural = "Informacje o raporcie Uszkodzone linki"
