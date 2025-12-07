from hypereditor.fields import HyperFieldPanel
from wagtail.admin.edit_handlers import FieldPanel, MultiFieldPanel, PublishingPanel
from wagtail.api import APIField

from mcod.cms.api.fields import HyperEditorJSONField, LocalizedHyperField
from mcod.cms.models.base import BasePage


class LandingPageIndex(BasePage):
    parent_page_types = ["cms.RootPage"]
    subpage_types = ["cms.LandingPage"]

    max_count = 1
    fixed_slug = "promotion"
    fixed_url_path = "promotion/"

    class Meta:
        verbose_name = "Lista stron startowych"
        verbose_name_plural = "Listy stron startowych"


class LandingPage(BasePage):
    body = LocalizedHyperField(default=None)
    body_en = LocalizedHyperField(default=None, blank=True, null=True)

    parent_page_types = [
        "cms.LandingPageIndex",
    ]

    subpage_types = []

    i18n_fields = BasePage.i18n_fields + [
        "body",
    ]

    api_fields = BasePage.api_fields + [APIField("body", serializer=HyperEditorJSONField(source="body_i18n"))]

    content_panels_pl = BasePage.content_panels + [HyperFieldPanel("body")]

    content_panels_en = BasePage.content_panels_en + [HyperFieldPanel("body_en")]

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
        verbose_name = "Strona startowa"
        verbose_name_plural = "Strony startowe"

    def get_copyable_fields(self):
        return super().get_copyable_fields() + ["body"]
