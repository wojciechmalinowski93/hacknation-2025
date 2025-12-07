from django.conf import settings
from hypereditor.fields import HyperFieldPanel
from wagtail.admin.edit_handlers import (
    FieldPanel,
    MultiFieldPanel,
    PublishingPanel,
    StreamFieldPanel,
)
from wagtail.api import APIField
from wagtail.api.v2.serializers import StreamField as StreamFieldSerializer
from wagtail.core.fields import StreamField

from mcod.cms.api.fields import HyperEditorJSONField, LocalizedHyperField
from mcod.cms.blocks.common import (
    BannerBlock,
    ImageChooserBlock,
    RawHTMLBlock,
    RichTextBlock,
    VideoBlock,
)
from mcod.cms.models.base import BasePage


class KBRootPage(BasePage):
    body = LocalizedHyperField(default=None, blank=True, null=True)
    body_en = LocalizedHyperField(default=None, blank=True, null=True)

    top_content_box = StreamField(
        [
            ("banner", BannerBlock(label="Baner reklamowy")),
            ("video", VideoBlock(label="Film")),
            (
                "text",
                RichTextBlock(features=settings.CMS_RICH_TEXT_FIELD_FEATURES, label="Tekst"),
            ),
            ("raw_html", RawHTMLBlock(label="Kod HTML")),
            ("image", ImageChooserBlock(label="Obraz")),
        ],
        default="",
        blank=True,
        verbose_name="Zawartość gównego bloku.",
        help_text="Wprowadź zawartość górnego bloku.",
    )

    bottom_content_box = StreamField(
        [
            ("banner", BannerBlock(label="Baner reklamowy")),
            ("video", VideoBlock(label="Film")),
            (
                "text",
                RichTextBlock(features=settings.CMS_RICH_TEXT_FIELD_FEATURES, label="Tekst"),
            ),
            ("raw_html", RawHTMLBlock(label="Kod HTML")),
            ("image", ImageChooserBlock(label="Obraz")),
        ],
        default="",
        blank=True,
        verbose_name="Zawartość dolnego bloku.",
        help_text="Wprowadź zawartość dolnego bloku.",
    )

    top_content_box_en = StreamField(
        [
            ("banner", BannerBlock(label="Baner reklamowy")),
            ("video", VideoBlock(label="Film")),
            (
                "text",
                RichTextBlock(features=settings.CMS_RICH_TEXT_FIELD_FEATURES, label="Tekst"),
            ),
            ("raw_html", RawHTMLBlock(label="Kod HTML")),
            ("image", ImageChooserBlock(label="Obraz")),
        ],
        default="",
        blank=True,
        verbose_name="Zawartość gównego bloku.",
        help_text="Wprowadź zawartość górnego bloku.",
    )

    bottom_content_box_en = StreamField(
        [
            ("banner", BannerBlock(label="Baner reklamowy")),
            ("video", VideoBlock(label="Film")),
            (
                "text",
                RichTextBlock(features=settings.CMS_RICH_TEXT_FIELD_FEATURES, label="Tekst"),
            ),
            ("raw_html", RawHTMLBlock(label="Kod HTML")),
            ("image", ImageChooserBlock(label="Obraz")),
        ],
        default="",
        blank=True,
        verbose_name="Zawartość dolnego bloku.",
        help_text="Wprowadź zawartość dolnego bloku.",
    )

    api_fields = BasePage.api_fields + [
        APIField(
            "top_content_box",
            serializer=StreamFieldSerializer(source="top_content_box_i18n"),
        ),
        APIField("body", serializer=HyperEditorJSONField(source="body_i18n")),
        APIField(
            "bottom_content_box",
            serializer=StreamFieldSerializer(source="bottom_content_box_i18n"),
        ),
    ]

    content_panels_pl = BasePage.content_panels_pl + [
        StreamFieldPanel("top_content_box"),
        StreamFieldPanel("bottom_content_box"),
        HyperFieldPanel("body"),
    ]

    content_panels_en = BasePage.content_panels_en + [
        StreamFieldPanel("top_content_box_en"),
        StreamFieldPanel("bottom_content_box_en"),
        HyperFieldPanel("body_en"),
    ]

    i18n_fields = BasePage.i18n_fields + [
        "body",
        "top_content_box",
        "bottom_content_box",
    ]

    parent_page_types = ["cms.RootPage"]
    subpage_types = ["cms.KBCategoryPage"]

    max_count = 1
    fixed_slug = "knowledgebase"
    fixed_url_path = "knowledgebase/"

    class Meta:
        verbose_name = "Baza wiedzy"
        verbose_name_plural = "Bazy wiedzy"

    def get_copyable_fields(self):
        return super().get_copyable_fields() + [
            "body",
            "top_content_box",
            "bottom_content_box",
        ]


class KBCategoryPage(BasePage):
    body = LocalizedHyperField(default=None, blank=True, null=True)
    body_en = LocalizedHyperField(default=None, blank=True, null=True)

    top_content_box = StreamField(
        [
            ("banner", BannerBlock(label="Baner reklamowy")),
            ("video", VideoBlock(label="Film")),
            (
                "text",
                RichTextBlock(features=settings.CMS_RICH_TEXT_FIELD_FEATURES, label="Tekst"),
            ),
            ("raw_html", RawHTMLBlock(label="Kod HTML")),
            ("image", ImageChooserBlock(label="Obraz")),
        ],
        default="",
        blank=True,
        verbose_name="Zawartość gównego bloku.",
        help_text="Wprowadź zawartość górnego bloku.",
    )

    bottom_content_box = StreamField(
        [
            ("banner", BannerBlock(label="Baner reklamowy")),
            ("video", VideoBlock(label="Film")),
            (
                "text",
                RichTextBlock(features=settings.CMS_RICH_TEXT_FIELD_FEATURES, label="Tekst"),
            ),
            ("raw_html", RawHTMLBlock(label="Kod HTML")),
            ("image", ImageChooserBlock(label="Obraz")),
        ],
        default="",
        blank=True,
        verbose_name="Zawartość dolnego bloku.",
        help_text="Wprowadź zawartość dolnego bloku.",
    )

    top_content_box_en = StreamField(
        [
            ("banner", BannerBlock(label="Baner reklamowy")),
            ("video", VideoBlock(label="Film")),
            (
                "text",
                RichTextBlock(features=settings.CMS_RICH_TEXT_FIELD_FEATURES, label="Tekst"),
            ),
            ("raw_html", RawHTMLBlock(label="Kod HTML")),
            ("image", ImageChooserBlock(label="Obraz")),
        ],
        default="",
        blank=True,
        verbose_name="Zawartość gównego bloku.",
        help_text="Wprowadź zawartość górnego bloku.",
    )

    bottom_content_box_en = StreamField(
        [
            ("banner", BannerBlock(label="Baner reklamowy")),
            ("video", VideoBlock(label="Film")),
            (
                "text",
                RichTextBlock(features=settings.CMS_RICH_TEXT_FIELD_FEATURES, label="Tekst"),
            ),
            ("raw_html", RawHTMLBlock(label="Kod HTML")),
            ("image", ImageChooserBlock(label="Obraz")),
        ],
        default="",
        blank=True,
        verbose_name="Zawartość dolnego bloku.",
        help_text="Wprowadź zawartość dolnego bloku.",
    )

    api_fields = BasePage.api_fields + [
        APIField(
            "top_content_box",
            serializer=StreamFieldSerializer(source="top_content_box_i18n"),
        ),
        APIField("body", serializer=HyperEditorJSONField(source="body_i18n")),
        APIField(
            "bottom_content_box",
            serializer=StreamFieldSerializer(source="bottom_content_box_i18n"),
        ),
    ]

    content_panels_pl = BasePage.content_panels_pl + [
        StreamFieldPanel("top_content_box"),
        StreamFieldPanel("bottom_content_box"),
        HyperFieldPanel("body"),
    ]

    content_panels_en = BasePage.content_panels_en + [
        StreamFieldPanel("top_content_box_en"),
        StreamFieldPanel("bottom_content_box_en"),
        HyperFieldPanel("body_en"),
    ]

    i18n_fields = BasePage.i18n_fields + [
        "body",
        "top_content_box",
        "bottom_content_box",
    ]

    parent_page_types = ["cms.KBRootPage"]
    subpage_types = ["cms.KBPage"]

    settings_panels = [
        MultiFieldPanel(
            [
                FieldPanel("slug"),
                FieldPanel("show_in_menus"),
            ],
            "Ustawienia strony",
        ),
    ]

    class Meta:
        verbose_name = "Kategoria stron w bazie wiedzy"
        verbose_name_plural = "Kategorie stron w bazie wiedzy"

    def get_copyable_fields(self):
        return super().get_copyable_fields() + [
            "body",
            "top_content_box",
            "bottom_content_box",
        ]


class KBPage(BasePage):
    body = StreamField(
        [
            ("banner", BannerBlock(label="Baner reklamowy")),
            ("video", VideoBlock(label="Film")),
            (
                "text",
                RichTextBlock(features=settings.CMS_RICH_TEXT_FIELD_FEATURES, label="Tekst"),
            ),
            ("raw_html", RawHTMLBlock(label="Kod HTML")),
            ("image", ImageChooserBlock(label="Obraz")),
        ],
        default=None,
        verbose_name="Treść strony.",
        help_text="Wprowadź treść dla tej strony.",
    )

    body_en = StreamField(
        [
            ("banner", BannerBlock(label="Baner reklamowy")),
            ("video", VideoBlock(label="Film")),
            (
                "text",
                RichTextBlock(features=settings.CMS_RICH_TEXT_FIELD_FEATURES, label="Tekst"),
            ),
            ("raw_html", RawHTMLBlock(label="Kod HTML")),
            ("image", ImageChooserBlock(label="Obraz")),
        ],
        default=None,
        blank=True,
        null=True,
        verbose_name="Treść strony.",
        help_text="Wprowadź treść dla tej strony.",
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
        "cms.KBCategoryPage",
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
        verbose_name = "Strona bazy wiedzy"
        verbose_name_plural = "Strona bazy wiedzy"

    def get_copyable_fields(self):
        return super().get_copyable_fields() + ["body"]


class KBQAPage(BasePage):
    parent_page_types = ["cms.KBRootPage"]
    subpage_types = []

    max_count = 1
    fixed_slug = "qa"
    fixed_url_path = "qa/"

    class Meta:
        verbose_name = "Strona pytań i odpowiedzi"
        verbose_name_plural = "Strony pytań i odpowiedzi"
