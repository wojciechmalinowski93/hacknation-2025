from ckeditor.fields import RichTextField
from django.db import models
from django.utils.translation import gettext_lazy as _
from modelcluster.contrib.taggit import ClusterTaggableManager
from modelcluster.fields import ParentalKey
from taggit.models import TaggedItemBase
from wagtail.admin.edit_handlers import FieldPanel, MultiFieldPanel, ObjectList, TabbedInterface
from wagtail.api import APIField

from mcod.cms.api import fields
from mcod.cms.api.serializers import NewsPageSerializer
from mcod.cms.models.base import BasePage


class NewsPageIndex(BasePage):
    parent_page_types = ["cms.RootPage"]
    subpage_types = ["cms.NewsPage"]
    api_meta_fields = ["children_count"]

    max_count = 1
    fixed_slug = "news"
    fixed_url_path = "news/"

    class Meta:
        verbose_name = "Lista aktualności"
        verbose_name_plural = "Listy aktualności"

    @property
    def children_count(self):
        return self.get_children().live().count()


class NewsTag(TaggedItemBase):
    content_object = ParentalKey("NewsPage", related_name="tagged_items", on_delete=models.CASCADE)


class NewsTagEn(TaggedItemBase):
    content_object = ParentalKey("NewsPage", related_name="tagged_items_en", on_delete=models.CASCADE)


class NewsPage(BasePage):
    parent_page_types = ["cms.NewsPageIndex"]
    subpage_types = []
    serializer_class = NewsPageSerializer
    indexable = True

    body = RichTextField(blank=True, verbose_name=_("Notes"))
    body_en = RichTextField(blank=True, verbose_name=_("Notes"))
    author = models.CharField(max_length=50, blank=True, verbose_name=_("Author"))
    author_en = models.CharField(max_length=50, blank=True, verbose_name=_("Author"))
    views_count = models.IntegerField(default=0)

    tags = ClusterTaggableManager(
        through=NewsTag,
        blank=True,
        related_name="news_page",
        help_text="Lista słów kluczowych oddzielonych przecinkami.",
    )
    tags_en = ClusterTaggableManager(
        through=NewsTagEn,
        blank=True,
        related_name="news_page_en",
        help_text="Lista słów kluczowych oddzielonych przecinkami.",
    )

    i18n_fields = BasePage.i18n_fields + ["body", "author", "tags"]

    api_fields = BasePage.api_fields + [
        APIField("body", serializer=fields.CharField(source="body_i18n")),
        APIField("author", serializer=fields.CharField(source="author_i18n")),
        APIField("tags", serializer=fields.TagsField(source="tags_i18n")),
        APIField("views_count"),
    ]

    content_panels_pl = BasePage.content_panels + [
        FieldPanel("body", classname="full", heading="Treść strony"),
        FieldPanel("tags"),
        FieldPanel("author", classname="full"),
    ]

    content_panels_en = BasePage.content_panels_en + [
        FieldPanel("body_en", classname="full", heading="Treść strony"),
        FieldPanel("tags_en"),
        FieldPanel("author_en", classname="full"),
    ]

    settings_panels = [
        MultiFieldPanel(
            [
                FieldPanel("slug"),
            ],
            "Ustawienia strony",
        ),
    ]

    edit_handler = TabbedInterface(
        [
            ObjectList(content_panels_pl, heading="Formularz (PL)"),
            ObjectList(content_panels_en, heading="Formularz (EN)"),
            ObjectList(settings_panels, heading="Ustawienia", classname="settings"),
        ]
    )

    class Meta(BasePage.Meta):
        verbose_name = "Aktualności"
        verbose_name_plural = "Aktualności"

    def get_copyable_fields(self):
        return super().get_copyable_fields() + ["body", "author"]

    @property
    def keywords_list(self):
        return [
            *[{"name": name, "language": "pl"} for name in self.tags.all().order_by("name").values_list("name", flat=True)],
            *[{"name": name, "language": "en"} for name in self.tags_en.all().order_by("name").values_list("name", flat=True)],
        ]
