from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.utils.translation import gettext_lazy as _
from model_utils import FieldTracker
from modeltrans.fields import TranslationField

from mcod.core.db.managers import TrashManager
from mcod.core.db.models import ExtendedModel, TrashModelBase
from mcod.core.managers import SoftDeletableManager
from mcod.lib.widgets import RichTextUploadingField

User = get_user_model()


CATEGORY_TYPES = (
    ("article", _("Article")),
    ("knowledge_base", _("Knowledge base")),
    ("unlisted", _("Not listed")),
)


class ArticleCategory(ExtendedModel):

    name = models.CharField(max_length=100, unique=True, verbose_name=_("name"))
    type = models.CharField(
        max_length=20,
        choices=CATEGORY_TYPES,
        verbose_name=_("type"),
        default="unlisted",
    )
    description = models.CharField(max_length=500, blank=True, verbose_name=_("Description"))

    created_by = models.ForeignKey(
        User,
        models.DO_NOTHING,
        blank=False,
        editable=False,
        null=True,
        verbose_name=_("Created by"),
        related_name="article_categories_created",
    )
    modified_by = models.ForeignKey(
        User,
        models.DO_NOTHING,
        blank=False,
        editable=False,
        null=True,
        verbose_name=_("Modified by"),
        related_name="article_categories_modified",
    )

    @property
    def image_url(self):
        return ""

    def __str__(self):
        return self.name_i18n

    i18n = TranslationField(fields=("name", "description"), required_languages=("pl",))

    tracker = FieldTracker()
    slugify_field = "name"

    objects = SoftDeletableManager()
    trash = TrashManager()

    class Meta:
        verbose_name = _("Article Category")
        verbose_name_plural = _("Article Categories")
        db_table = "article_category"
        default_manager_name = "objects"
        indexes = [
            GinIndex(fields=["i18n"]),
        ]


class Article(ExtendedModel):

    title = models.CharField(max_length=300, verbose_name=_("Title"))
    notes = RichTextUploadingField(verbose_name=_("Notes"), null=True)
    license_old_id = models.CharField(max_length=20, blank=True, null=True, verbose_name=_("License ID"))
    license = models.ForeignKey(
        "licenses.License",
        on_delete=models.DO_NOTHING,
        blank=True,
        null=True,
        verbose_name=_("License ID"),
    )
    author = models.CharField(max_length=50, blank=True, null=True, verbose_name=_("Author"))
    category = models.ForeignKey(ArticleCategory, on_delete=models.PROTECT, verbose_name=_("Category"))
    tags = models.ManyToManyField(
        "tags.Tag",
        db_table="article_tag",
        blank=True,
        verbose_name=_("Tags"),
        related_name="articles",
        related_query_name="article",
    )
    datasets = models.ManyToManyField(
        "datasets.Dataset",
        db_table="article_dataset",
        verbose_name=_("Datasets"),
        related_name="articles",
        related_query_name="article",
    )

    created_by = models.ForeignKey(
        User,
        models.DO_NOTHING,
        blank=False,
        editable=False,
        null=True,
        verbose_name=_("Created by"),
        related_name="articles_created",
    )
    modified_by = models.ForeignKey(
        User,
        models.DO_NOTHING,
        blank=False,
        editable=False,
        null=True,
        verbose_name=_("Modified by"),
        related_name="articles_modified",
    )

    @classmethod
    def accusative_case(cls):
        return _("acc: Article")

    def __str__(self):
        return self.title

    def published_datasets(self):
        return self.datasets.filter(status="published")

    @property
    def frontend_url(self):
        return f"/article/{self.ident}"

    @property
    def frontend_absolute_url(self):
        return self._get_absolute_url(self.frontend_url)

    @property
    def frontend_preview_url(self):
        return self._get_absolute_url(f"/knowledge-base/preview/{self.id}")

    @property
    def is_knowledge_base(self):
        return bool(self.category.type == "knowledge_base")

    @property
    def is_news(self):
        return bool(self.category.type == "article")

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

    def migrate_news_to_cms(self):
        if not self.is_news:
            return
        news_index_model = apps.get_model("cms.NewsPageIndex")
        news_model = apps.get_model("cms.NewsPage")
        news_ct = ContentType.objects.get_for_model(news_model)
        news_index = news_index_model.objects.first()
        if not news_index:
            root_model = apps.get_model("cms.RootPage")
            news_index_ct = ContentType.objects.get_for_model(news_index_model)
            root = root_model.objects.first()
            if root:
                news_index = news_index_model(
                    title="Aktualności",
                    title_en="News",
                    content_type=news_index_ct,
                    show_in_menus=True,
                )
                root.add_child(instance=news_index)
        if not news_index.get_children().filter(title=self.title).exists():
            news = news_model(
                title=self.title,
                title_en=self.title_en or "",
                body=self.notes,
                body_en=self.notes_en or "",
                author=self.author or "",
                author_en=self.author or "",
                first_published_at=self.created,
                last_published_at=self.modified,
                views_count=self.views_count,
                content_type=news_ct,
                show_in_menus=True,
                live=bool(self.status == "published"),
            )
            news_index.add_child(instance=news)
            tags_pl = self.tags.filter(language="pl").values_list("name", flat=True)
            tags_en = self.tags.filter(language="en").values_list("name", flat=True)
            for tag in tags_pl:
                news.tags.add(tag)
            for tag in tags_en:
                news.tags_en.add(tag)
            if tags_pl or tags_en:
                news.save()

    i18n = TranslationField(fields=("title", "notes"))
    tracker = FieldTracker()
    slugify_field = "title"

    objects = SoftDeletableManager()
    trash = TrashManager()

    class Meta:
        verbose_name = _("Article")
        verbose_name_plural = _("Articles")
        db_table = "article"
        default_manager_name = "objects"
        indexes = [
            GinIndex(fields=["i18n"]),
        ]


class ArticleTrash(Article, metaclass=TrashModelBase):
    class Meta:
        proxy = True
        verbose_name = _("Trash")
        verbose_name_plural = _("Trash")
