from hypereditor.fields import HyperFieldPanel
from wagtail.admin.edit_handlers import StreamFieldPanel
from wagtail.api import APIField
from wagtail.api.v2.serializers import StreamField as StreamFieldSerializer
from wagtail.core.fields import StreamField

from mcod.cms.api.fields import HyperEditorJSONField, LocalizedHyperField
from mcod.cms.blocks.common import CarouselBlock
from mcod.cms.models.base import BasePage

# Image limit in footer to handle many sets of logos depends on contrast mode
# For example: 5 normal logos, and 5 logos for yellow_black, etc...
# Currently we have 4 different contrast modes.
# Logos are filtered in frontend base on the file name.
FOOTER_LOGOS_LIMIT = 20


class RootPage(BasePage):
    over_login_section_cb = StreamField(
        CarouselBlock(max_num=5, required=False),
        default=None,
        blank=True,
        verbose_name="Blok nad paskiem logowania",
        help_text="TODO: napisać",
    )
    over_search_field_cb = StreamField(
        CarouselBlock(max_num=5, required=False),
        default=None,
        blank=True,
        verbose_name="Blok pod wyszukiwarką",
        help_text="TODO: napisać",
    )
    over_latest_news_cb = StreamField(
        CarouselBlock(max_num=5, required=False),
        default=None,
        blank=True,
        verbose_name='Blok nad sekcją "Aktualności"',
        help_text="TODO: napisać",
    )
    over_login_section_cb_en = StreamField(
        CarouselBlock(max_num=5, required=False),
        default=None,
        blank=True,
        verbose_name="Blok nad paskiem logowania",
        help_text="TODO: napisać",
    )
    over_search_field_cb_en = StreamField(
        CarouselBlock(max_num=5, required=False),
        default=None,
        blank=True,
        verbose_name="Blok pod wyszukiwarką",
        help_text="TODO: napisać",
    )
    over_latest_news_cb_en = StreamField(
        CarouselBlock(max_num=5, required=False),
        default=None,
        blank=True,
        verbose_name='Blok nad sekcją "Aktualności"',
        help_text="TODO: napisać",
    )

    footer_nav = LocalizedHyperField(default=None, blank=True, null=True, verbose_name="Stopka - sekcja nawigacji")
    footer_nav_en = LocalizedHyperField(default=None, blank=True, null=True, verbose_name="Stopka - sekcja nawigacji")

    footer_logos = StreamField(
        CarouselBlock(max_num=FOOTER_LOGOS_LIMIT, required=False),
        default=None,
        blank=True,
        verbose_name="Stopka - sekcja logo",
    )
    footer_logos_en = StreamField(
        CarouselBlock(max_num=FOOTER_LOGOS_LIMIT, required=False),
        default=None,
        blank=True,
        verbose_name="Stopka - sekcja logo",
    )

    parent_page_types = ["wagtailcore.Page"]

    fixed_url_path = ""

    api_fields = BasePage.api_fields + [
        APIField(
            "over_login_section_cb",
            serializer=StreamFieldSerializer(source="over_login_section_cb_i18n"),
        ),
        APIField(
            "over_search_field_cb",
            serializer=StreamFieldSerializer(source="over_search_field_cb_i18n"),
        ),
        APIField(
            "over_latest_news_cb",
            serializer=StreamFieldSerializer(source="over_latest_news_cb_i18n"),
        ),
        APIField("footer_nav", serializer=HyperEditorJSONField(source="footer_nav_i18n")),
        APIField("footer_logos", serializer=StreamFieldSerializer(source="footer_logos_i18n")),
    ]

    content_panels_pl = BasePage.content_panels_pl + [
        StreamFieldPanel("over_login_section_cb"),
        StreamFieldPanel("over_search_field_cb"),
        StreamFieldPanel("over_latest_news_cb"),
        HyperFieldPanel("footer_nav"),
        StreamFieldPanel("footer_logos"),
    ]

    content_panels_en = BasePage.content_panels_en + [
        StreamFieldPanel("over_login_section_cb_en"),
        StreamFieldPanel("over_search_field_cb_en"),
        StreamFieldPanel("over_latest_news_cb_en"),
        HyperFieldPanel("footer_nav_en"),
        StreamFieldPanel("footer_logos_en"),
    ]

    i18n_fields = BasePage.i18n_fields + [
        "over_login_section_cb",
        "over_search_field_cb",
        "over_latest_news_cb",
        "footer_nav",
        "footer_logos",
    ]

    class Meta:
        verbose_name = "Strona główna"
        verbose_name_plural = "Strony główne"

    def get_copyable_fields(self):
        page_fields = [
            "over_login_section_cb",
            "over_search_field_cb",
            "over_latest_news_cb",
            "footer_nav",
            "footer_logos",
        ]
        return super().get_copyable_fields() + page_fields
