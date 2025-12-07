import itertools
import json
import logging
import os
from types import SimpleNamespace
from typing import List, Optional
from uuid import uuid4

from constance import config
from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import JSONField
from django.contrib.postgres.indexes import GinIndex
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Max, Q, Sum
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.utils.functional import cached_property
from django.utils.safestring import mark_safe
from django.utils.timezone import now
from django.utils.translation import get_language, gettext_lazy as _, override
from model_utils import FieldTracker

from mcod import settings
from mcod.core import model_validators, signals as core_signals
from mcod.core.api.rdf import signals as rdf_signals
from mcod.core.api.search import signals as search_signals
from mcod.core.api.search.tasks import update_document_task
from mcod.core.db.managers import TrashManager
from mcod.core.db.models import ExtendedModel, TrashModelBase, update_watcher
from mcod.core.storages import get_storage
from mcod.counters.models import ResourceDownloadCounter, ResourceViewCounter
from mcod.datasets.managers import DatasetManager, SupplementManager
from mcod.datasets.signals import remove_related_resources
from mcod.datasets.tasks import archive_resources_files, change_archive_symlink_name
from mcod.lib.model_sanitization import (
    SanitizedCharField,
    SanitizedJSONField,
    SanitizedTextField,
    SanitizedTranslationField,
)
from mcod.regions.models import Region
from mcod.watchers.tasks import update_model_watcher_task

logger = logging.getLogger("mcod")

User = get_user_model()

UPDATE_FREQUENCY = (
    ("daily", _("Daily")),
    ("weekly", _("Weekly")),
    ("monthly", _("Monthly")),
    ("quarterly", _("Quarterly")),
    ("everyHalfYear", _("Every half year")),
    ("yearly", _("Yearly")),
    ("irregular", _("Irregular")),
    ("notPlanned", _("Not planned")),
    ("notApplicable", _("Not applicable")),  # deprecated value of update_frequency - OTD-1231
)
UPDATE_FREQUENCY_NOTIFICATION_RANGES = {
    "yearly": (1, 365),
    "everyHalfYear": (1, 182),
    "quarterly": (1, 90),
    "monthly": (1, 30),
    "weekly": (1, 6),
}
UPDATE_NOTIFICATION_FREQUENCY_DEFAULT_VALUES = {
    "yearly": 7,
    "everyHalfYear": 7,
    "quarterly": 7,
    "monthly": 3,
    "weekly": 1,
}

TYPE = (
    ("application", _("application")),
    ("dataset", _("dataset")),
    ("article", _("article")),
)


def archives_upload_to(instance, filename):
    """Creates an archive file path."""
    return f"{instance.archive_folder_name}/{filename}"


LICENSE_CONDITION_LABELS = {
    "private": {
        "source": _(
            "The user should inform about the source, time of creation and"
            " obtaining private data from the entity providing the data (supplier)"
        ),
        "modification": _(
            "The user should inform about the processing of the used private data" " (if he modifies it in any way)"
        ),
        "responsibilities": _(
            "The scope of the responsibility of the entity providing private data (suppliers) for the" " provided data"
        ),
        "db_or_copyrighted": _(
            "Conditions for the use of private data with the features of a work or subject of"
            " related rights within the meaning of the Act of February 4, 1994 on"
            " copyright and related rights or constituting a database within the meaning"
            " of the Act of July 27, 2001 on the protection of databases,"
            " or covered by plant variety rights within the meaning of the Act of 26 June 2003"
            " on the legal protection of plant varieties, to which the entity providing private"
            " data (suppliers) has rights (Article 36 (2) (1) of the Act of 11"
            " August 2021 on open data and re-use of public sector information)"
        ),
        "custom_description": mark_safe(
            _(
                "The user should inform about the source, time of creation and"
                " obtaining private data from the entity providing the data (supplier) <br><br> "
                "The user should inform about the processing of the used private data"
                " (if he modifies it in any way) <br><br> The scope of the responsibility of the"
                " entity providing private data (suppliers) for the provided data"
            )
        ),
    },
    "public": {
        "source": _(
            "The user should inform about the source, time of creation and obtaining public sector"
            " information from the obliged entity (supplier)"
        ),
        "modification": _(
            "The user should inform about the processing of public sector" " information to re-use (when modifying it in any way)"
        ),
        "responsibilities": _(
            "The scope of the responsibility of the obliged entity (supplier) for shared" " public sector information"
        ),
        "db_or_copyrighted": _(
            "Conditions for the re-use of public sector information with the features of a work"
            " or subject of related rights within the meaning of the provisions of the"
            " Act of February 4, 1994 on copyright and related rights or constituting a database"
            " within the meaning of the provisions of the Act of July 27, 2001 on the protection"
            " of databases or covered by plant variety rights within the meaning of the Act"
            " of 26 June 2003 on the legal protection of plant varieties to which the obligated"
            " entity (suppliers) has rights (14 (2) of the Act of 11 August 2021 on open data"
            " and re-use public sector information)"
        ),
        "personal_data": _(
            "Conditions for the re-use of public sector information constituting or containing personal"
            " data (Article 15 (1) (4) of the Act of 11 August 2021 on open data and re-use"
            " of public sector information)"
        ),
        "custom_description": mark_safe(
            _(
                "The user should inform about the source, time of creation and obtaining public sector"
                " information from the obliged entity (supplier) <br><br> "
                "The user should inform about the processing of public sector"
                " information to re-use (when modifying it in any way) <br><br> The scope of the responsibility"
                " of the obliged entity (supplier) for shared public sector information"
            )
        ),
    },
}
CC_BY_40_RESPONSIBILITIES_LABELS = {
    "private": _(
        "The scope of the responsibility of the entity providing private data (suppliers) for the shared data"
        " in accordance with the terms of the CC BY 4.0 license"
    ),
    "public": _(
        "The scope of the responsibility of the obliged entity (supplier) providing public sector information"
        " in accordance with the terms of the CC BY 4.0 license"
    ),
}


class Dataset(ExtendedModel):
    LICENSE_CC0 = 1
    LICENSE_CC_BY = 2
    LICENSE_CC_BY_SA = 3
    LICENSE_CC_BY_NC = 4
    LICENSE_CC_BY_NC_SA = 5
    LICENSE_CC_BY_ND = 6
    LICENSE_CC_BY_NC_ND = 7

    LICENSE_CC0_TUPLE = (LICENSE_CC0, "CC0 1.0")
    LICENSES = (
        LICENSE_CC0_TUPLE,
        (LICENSE_CC_BY, "CC BY 4.0"),
        (LICENSE_CC_BY_SA, "CC BY-SA 4.0"),
        (LICENSE_CC_BY_NC, "CC BY-NC 4.0"),
        (LICENSE_CC_BY_NC_SA, "CC BY-NC-SA 4.0"),
        (LICENSE_CC_BY_ND, "CC BY-ND 4.0"),
        (LICENSE_CC_BY_NC_ND, "CC BY-NC-ND 4.0"),
    )
    LICENSE_CODE_TO_NAME = dict(LICENSES)

    SIGNALS_MAP = {
        "updated": (
            rdf_signals.update_graph_with_conditional_related,
            search_signals.update_document_with_related,
            core_signals.notify_updated,
        ),
        "published": (
            rdf_signals.create_graph,
            search_signals.update_document_with_related,
            core_signals.notify_published,
        ),
        "restored": (
            rdf_signals.create_graph,
            search_signals.update_document_with_related,
            core_signals.notify_restored,
        ),
        "removed": (
            remove_related_resources,
            rdf_signals.delete_graph,
            search_signals.remove_document_with_related,
            core_signals.notify_removed,
        ),
        "post_m2m_added": (
            search_signals.update_document_related,
            rdf_signals.update_graph,
        ),
        "post_m2m_removed": (
            search_signals.update_document_related,
            rdf_signals.update_graph,
        ),
        "post_m2m_cleaned": (
            search_signals.update_document_related,
            rdf_signals.update_graph,
        ),
    }
    ext_ident = models.CharField(
        max_length=36,
        blank=True,
        editable=False,
        verbose_name=_("external identifier"),
        help_text=_("external identifier of dataset taken during import process (optional)"),
    )
    title = SanitizedCharField(
        max_length=300,
        null=True,
        verbose_name=_("Title"),
        validators=[model_validators.illegal_character_validator],
    )
    version = models.CharField(max_length=100, blank=True, null=True, verbose_name=_("Version"))
    url = models.CharField(max_length=1000, blank=True, null=True, verbose_name=_("Url"))
    notes = SanitizedTextField(
        verbose_name=_("Notes"), null=True, blank=False, validators=[model_validators.illegal_character_validator]
    )

    license_chosen = models.PositiveSmallIntegerField(blank=True, null=True, default=None, verbose_name="", choices=LICENSES)

    license_old_id = models.CharField(max_length=20, blank=True, null=True, verbose_name=_("License ID"))
    license = models.ForeignKey(
        "licenses.License",
        on_delete=models.DO_NOTHING,
        blank=True,
        null=True,
        verbose_name=_("License ID"),
    )

    license_condition_db_or_copyrighted = SanitizedTextField(
        blank=True,
        null=True,
        verbose_name=_("Condition for data with features of work with copy rights or database"),
    )
    license_condition_personal_data = SanitizedCharField(
        max_length=300,
        blank=True,
        null=True,
        verbose_name=_("Condition for data containing personal data"),
    )
    license_condition_modification = models.NullBooleanField(
        null=True,
        blank=True,
        default=None,
        verbose_name=_("Condition for possible processing of data"),
    )
    license_condition_original = models.NullBooleanField(null=True, blank=True, default=None)
    license_condition_responsibilities = SanitizedTextField(
        blank=True,
        null=True,
        verbose_name=_("Condition for scope of responsibilities for data"),
    )
    license_condition_cc40_responsibilities = models.NullBooleanField(null=True, blank=True, default=None, verbose_name="")
    license_condition_source = models.NullBooleanField(
        null=True,
        blank=True,
        default=None,
        verbose_name=_("Condition for informing about the source of data"),
    )
    license_condition_timestamp = models.NullBooleanField(null=True, blank=True)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="datasets",
        verbose_name=_("Institution"),
    )
    customfields = SanitizedJSONField(blank=True, null=True, verbose_name=_("Customfields"))
    update_frequency = models.CharField(max_length=50, blank=True, null=True, verbose_name=_("Update frequency"))
    is_update_notification_enabled = models.BooleanField(default=True, verbose_name=_("turn on notification"))
    has_dynamic_data = models.NullBooleanField(verbose_name=_("dynamic data"))
    has_high_value_data = models.NullBooleanField(verbose_name=_("has high value data"))
    has_high_value_data_from_ec_list = models.NullBooleanField(verbose_name=_("has high value data from the EC list"))
    has_research_data = models.NullBooleanField(verbose_name=_("has research data"))
    update_notification_frequency = models.PositiveSmallIntegerField(
        null=True, blank=True, verbose_name=_("set notifications frequency")
    )
    update_notification_recipient_email = models.EmailField(
        blank=True, verbose_name=_("the person who is the notifications recipient")
    )

    category = models.ForeignKey(
        "categories.Category",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name=_("Category"),
        limit_choices_to=Q(code=""),
    )

    categories = models.ManyToManyField(
        "categories.Category",
        db_table="dataset_category",
        verbose_name=_("Categories"),
        related_name="datasets",
        related_query_name="dataset",
        limit_choices_to=~Q(code=""),
    )

    tags = models.ManyToManyField(
        "tags.Tag",
        db_table="dataset_tag",
        blank=False,
        verbose_name=_("Tag"),
        related_name="datasets",
        related_query_name="dataset",
    )

    created_by = models.ForeignKey(
        User,
        models.DO_NOTHING,
        blank=False,
        editable=False,
        null=True,
        verbose_name=_("Created by"),
        related_name="datasets_created",
    )
    modified_by = models.ForeignKey(
        User,
        models.DO_NOTHING,
        blank=False,
        editable=False,
        null=True,
        verbose_name=_("Modified by"),
        related_name="datasets_modified",
    )
    source = models.ForeignKey(
        "harvester.DataSource",
        models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("source"),
        related_name="datasource_datasets",
    )
    verified = models.DateTimeField(blank=True, default=now, verbose_name=_("Update date"))
    downloads_count = models.PositiveIntegerField(verbose_name=_("download counter"), default=0)
    image = models.ImageField(
        max_length=200,
        storage=get_storage("datasets"),
        upload_to="dataset_logo/%Y%m%d",
        blank=True,
        null=True,
        verbose_name=_("Image URL"),
    )
    image_alt = SanitizedCharField(max_length=255, blank=True, verbose_name=_("Alternative text"))
    dcat_vocabularies = JSONField(blank=True, null=True, verbose_name=_("Controlled Vocabularies"))
    archived_resources_files = models.FileField(
        storage=get_storage("datasets_archives"),
        blank=True,
        null=True,
        upload_to=archives_upload_to,
        max_length=2000,
        verbose_name=_("Archived resources files"),
    )
    license_condition_default_cc40 = models.NullBooleanField(null=True, blank=True, default=None, verbose_name="")
    license_condition_custom_description = SanitizedTextField(blank=True, null=True, verbose_name=_("Custom CC BY 40 conditions"))
    is_promoted = models.BooleanField(verbose_name=_("promoting the dataset"), default=False)

    def __str__(self):
        # need to use str func because title CharField was set with null=True
        return str(self.title)

    @property
    def archive_folder_name(self) -> str:
        """Returns a dataset folder name for archive files."""
        return f"dataset_{self.pk}"

    def delete(self, using=None, soft=True, permanent=False, *args, **kwargs):
        if self.is_imported:
            permanent = True
            logger.debug(f"Permanent removing imported dataset: {self.pk}")
        if self.is_promoted:
            self.is_promoted = False
        super().delete(using=using, soft=soft, permanent=permanent, *args, **kwargs)

    @cached_property
    def has_table(self):
        return self.resources.published().filter(has_table=True).exists()

    @cached_property
    def has_map(self):
        return self.resources.published().filter(has_map=True).exists()

    @cached_property
    def has_chart(self):
        return self.resources.published().filter(has_chart=True).exists()

    @property
    def comment_editors(self):
        emails = []
        if self.source:
            emails.extend(self.source.emails_list)
        else:
            if self.update_notification_recipient_email:
                emails.append(self.update_notification_recipient_email)
            elif self.modified_by:
                emails.append(self.modified_by.email)
            else:
                emails.extend(user.email for user in self.organization.users.all())
        return emails

    @property
    def comment_mail_recipients(self):
        return [
            config.CONTACT_MAIL,
        ] + self.comment_editors

    @property
    def is_imported(self):
        return bool(self.source)

    @property
    def is_imported_from_ckan(self):
        return self.is_imported and self.source.is_ckan

    @property
    def is_imported_from_xml(self):
        return self.is_imported and self.source.is_xml

    @property
    def is_published(self):
        return self.status == "published"

    @property
    def institution(self):
        return self.organization

    @property
    def source_title(self):
        return self.source.name if self.source else None

    @property
    def source_type(self) -> Optional[str]:
        return self.source.source_type if self.source else None

    @property
    def source_url(self):
        return self.source.portal_url if self.source else None

    @property
    def title_as_link(self):
        return self.mark_safe(f'<a href="{self.admin_change_url}">{self.title}</a>')

    @property
    def formats(self):
        items = [x.formats_list for x in self.resources.published() if x.formats_list]
        return sorted(set([item for sublist in items for item in sublist]))

    @property
    def types(self):
        return list(self.resources.published().values_list("type", flat=True).distinct())

    @property
    def frontend_url(self):
        return f"/dataset/{self.ident}"

    @property
    def frontend_absolute_url(self):
        return self._get_absolute_url(self.frontend_url)

    @property
    def openness_scores(self):
        return list(set(res.openness_score for res in self.resources.published()))

    @property
    def keywords_list(self):
        return [tag.to_dict for tag in self.tags.all()]

    @property
    def keywords(self):
        return self.tags

    @property
    def tags_list_as_str(self):
        return ", ".join(sorted([str(tag) for tag in self.tags.all()], key=str.lower))

    def tags_as_str(self, lang):
        return ", ".join(sorted([tag.name for tag in self.tags.filter(language=lang)], key=str.lower))

    @property
    def categories_list_as_html(self):
        categories = self.categories.all()
        return self.mark_safe("<br>".join(category.title for category in categories)) if categories else "-"

    @property
    def categories_list_str(self):
        return ", ".join(self.categories.all().values_list("title", flat=True))

    @property
    def license_code(self):
        license_ = self.LICENSE_CC0
        if any(
            [
                self.license_condition_source,
                self.license_condition_modification,
                self.license_condition_responsibilities,
                self.license_condition_cc40_responsibilities,
                self.license_condition_default_cc40,
                self.license_condition_custom_description,
            ]
        ):
            license_ = self.LICENSE_CC_BY
        if self.license_chosen and self.license_chosen > license_:
            license_ = self.license_chosen
        return license_

    @property
    def license_name(self):
        return self.LICENSE_CODE_TO_NAME.get(self.license_code)

    @property
    def license_link(self):
        url = settings.LICENSES_LINKS.get(self.license_name)
        return f"{url}legalcode.{get_language()}"

    @property
    def license_description(self):
        return self.license.title if self.license and self.license.title else ""

    @property
    def last_modified_resource(self):
        return self.resources.all().aggregate(Max("modified"))["modified__max"]

    last_modified_resource.fget.short_description = _("modified")

    @property
    def is_license_set(self):
        return any(
            [
                self.license,
                self.license_condition_db_or_copyrighted,
                self.license_condition_modification,
                self.license_condition_original,
                self.license_condition_responsibilities,
                self.license_condition_cc40_responsibilities,
                self.license_condition_default_cc40,
                self.license_condition_custom_description,
            ]
        )

    @property
    def followers_count(self):
        return self.users_following.count()

    @property
    def published_resources_count(self):
        return self.resources.published().count()

    @property
    def visualization_types(self):
        return list(set(itertools.chain(*[r.visualization_types for r in self.resources.published()])))

    @property
    def model_name(self):
        return self._meta.model_name

    @classmethod
    def accusative_case(cls):
        return _("acc: Dataset")

    @property
    def image_url(self):
        return self.image.url if self.image else ""

    @property
    def image_absolute_url(self):
        return self._get_absolute_url(self.image_url, use_lang=False) if self.image_url else ""

    @property
    def dataset_logo(self):
        if self.image_absolute_url:
            return self.mark_safe(
                '<a href="%s" target="_blank"><img src="%s" width="%d" alt="%s" /></a>'
                % (
                    self.admin_change_url,
                    self.image_absolute_url,
                    100,
                    self.image_alt if self.image_alt else "",
                )
            )
        return ""

    @property
    def computed_downloads_count(self):
        return (
            ResourceDownloadCounter.objects.filter(resource__dataset_id=self.pk).aggregate(count_sum=Sum("count"))["count_sum"]
            or 0
        )

    @property
    def computed_views_count(self):
        return (
            ResourceViewCounter.objects.filter(resource__dataset_id=self.pk).aggregate(count_sum=Sum("count"))["count_sum"] or 0
        )

    @property
    def dga_resources_titles(self) -> List[str]:
        """
        Returns a list of all DGA resources titles in Dataset.
        Logs an error if more than one DGA Resource is found in the Dataset.

        Used in delete confirmation HTML templates.
        """
        dga_resources_in_dataset = self.resources.filter(contains_protected_data=True, status="published").values_list(
            "title", flat=True
        )
        count_dga_resources: int = dga_resources_in_dataset.count()
        if count_dga_resources > 1:
            logger.error(f"Found {count_dga_resources} in dataset with pk: {self.pk}")

        return list(dga_resources_in_dataset)

    def to_rdf_graph(self):
        schema = self.get_rdf_serializer_schema()
        return schema(many=False).dump(self) if schema else None

    def as_sparql_create_query(self):
        g = self.to_rdf_graph()
        data = "".join([f"{s.n3()} {p.n3()} {o.n3()} . " for s, p, o in g.triples((None, None, None))])
        namespaces_dict = {prefix: ns for prefix, ns in g.namespaces()}
        return "INSERT DATA { %(data)s }" % {"data": data}, namespaces_dict

    def clean(self):
        _range = UPDATE_FREQUENCY_NOTIFICATION_RANGES.get(self.update_frequency)
        if (
            _range
            and self.update_notification_frequency
            and self.update_notification_frequency not in range(_range[0], _range[1] + 1)
        ):
            msg = _("The value must be between %(min)s and %(max)s") % {
                "min": _range[0],
                "max": _range[1],
            }
            raise ValidationError({"update_notification_frequency": msg})

    def send_dataset_comment_mail(self, comment):
        with override("pl"):
            title = self.title.replace("\n", " ").replace("\r", "")
            version = _(" (version %(version)s)") % {"version": self.version} if self.version else ""
            msg_template = _("On the data set %(title)s%(version)s [%(url)s] was posted a comment:")
            msg = msg_template % {
                "title": title,
                "version": version,
                "url": self.frontend_absolute_url,
            }
            html_msg = msg_template % {
                "title": title,
                "version": version,
                "url": f'<a href="{self.frontend_absolute_url}">{self.frontend_absolute_url}</a>',
            }
            context = {
                "host": settings.BASE_URL,
                "url": self.frontend_absolute_url,
                "comment": comment,
                "dataset": self,
                "message": msg,
                "html_message": html_msg,
                "test": bool(settings.DEBUG and config.TESTER_EMAIL),
            }
            subject = _("A comment was posted on the data set %(title)s%(version)s") % {
                "title": title,
                "version": version,
            }
            _plain = "mails/dataset-comment.txt"
            _html = "mails/dataset-comment.html"
            msg_plain = render_to_string(_plain, context=context)
            msg_html = render_to_string(_html, context=context)

            return self.send_mail(
                subject,
                msg_plain,
                config.SUGGESTIONS_EMAIL,
                ([config.TESTER_EMAIL] if settings.DEBUG and config.TESTER_EMAIL else self.comment_mail_recipients),
                html_message=msg_html,
            )

    @property
    def frequency_display(self):
        return dict(UPDATE_FREQUENCY).get(self.update_frequency)

    @property
    def dataset_update_notification_recipient(self):
        return self.update_notification_recipient_email or self.modified_by.email

    @property
    def regions(self):
        has_no_region_resources = self.resources.published().filter(is_removed=False, regions__isnull=True).exists()
        return Region.objects.for_dataset_with_id(self.pk, has_no_region_resources=has_no_region_resources)

    @property
    def regions_str(self):
        return "; ".join(list(self.regions.values_list("hierarchy_label_i18n", flat=True)))

    @cached_property
    def showcases_published(self):
        return self.showcases.filter(status="published")

    @cached_property
    def supplement_docs(self):
        return self.supplements.all()

    @property
    def supplements_str(self):
        return ";".join([x.name_csv for x in self.supplement_docs])

    def archive_files(self):
        archive_resources_files.s(dataset_id=self.pk).apply_async(countdown=settings.DATASET_ARCHIVE_FILES_TASK_DELAY)

    @classmethod
    def get_license_data(cls, name, lang=None):
        data = None
        if name not in [
            "CC0",
            "CCBY",
            "CCBY-SA",
            "CCBY-NC",
            "CCBY-NC-SA",
            "CCBY-ND",
            "CCBY-NC-ND",
        ]:
            return data
        with open(os.path.join(settings.DATA_DIR, "datasets", "licenses.json")) as fp:
            json_data = json.load(fp)
            try:
                lang = lang or get_language()
                data = json_data[lang][name]
                data = SimpleNamespace(id=uuid4(), **data)
            except Exception as exc:
                logger.debug(exc)
        return data

    @classmethod
    def send_dataset_update_reminder_mails(cls, datasets):
        data = []
        for ds in datasets:
            context = {
                "dataset_title": ds.title,
                "url": ds.frontend_absolute_url,
                "host": settings.BASE_URL,
            }
            subject = ds.title.replace("\n", "").replace("\r", "")
            msg_plain = render_to_string("mails/dataset-update-reminder.txt", context=context)
            msg_html = render_to_string("mails/dataset-update-reminder.html", context=context)
            data.append(
                {
                    "subject": subject,
                    "body": msg_plain,
                    "from_email": config.NO_REPLY_EMAIL,
                    "to": [ds.dataset_update_notification_recipient],
                    "alternatives": [(msg_html, "text/html")],
                }
            )
        return cls.send_mail_messages(data)

    @property
    def archived_resources_files_url(self):
        return (
            "{}/datasets/{}/resources/files/download".format(settings.API_URL, self.ident)
            if self.archived_resources_files
            else None
        )

    @property
    def resources_files_list(self):
        resourcefile_model = apps.get_model("resources", "ResourceFile")
        return resourcefile_model.objects.files_details_list(dataset_id=self.pk)

    @property
    def archived_resources_files_media_url(self):
        if self.archived_resources_files:
            real_path = os.path.realpath(self.archived_resources_files.path)
            base_url = self.archived_resources_files.url.rsplit("/", 1)
            full_url = self._get_absolute_url(
                base_url=f"{base_url[0]}/",
                url=os.path.basename(real_path),
                use_lang=False,
            )
            return self.mark_safe("<a href='%s'>%s</a>" % (full_url, self.archived_resources_files.name))
        return ""

    @property
    def institution_type(self):
        return self.organization.institution_type if self.organization.institution_type in LICENSE_CONDITION_LABELS else "public"

    @property
    def license_condition_labels(self):
        return LICENSE_CONDITION_LABELS[self.institution_type]

    @property
    def current_condition_descriptions(self):
        labels = {"custom_description": self.license_condition_labels["responsibilities"]}
        descriptions = {}
        for key, val in labels.items():
            condition_field = f"license_condition_{key}"
            if getattr(self, condition_field) and key == "cc40_responsibilities":
                descriptions[condition_field] = f'{labels["responsibilities"]}: \n{val}'
            elif getattr(self, condition_field):
                descriptions[condition_field] = val
        return descriptions

    @property
    def formatted_condition_descriptions(self):
        user_input_conditions = [
            "license_condition_responsibilities",
            "license_condition_personal_data",
            "license_condition_db_or_copyrighted",
            "license_condition_custom_description",
        ]
        conditions = _("This dataset can be used under following conditions: ")
        descriptions = self.current_condition_descriptions
        terms = []
        for key, val in descriptions.items():
            if key in user_input_conditions:
                condition_text = f"{val}: {getattr(self, key)}"
            else:
                condition_text = str(val)
            terms.append(condition_text)
        return conditions + "\n".join([term for term in terms if term]) if terms else ""

    i18n = SanitizedTranslationField(fields=("title", "notes", "image_alt"))
    objects = DatasetManager()
    trash = TrashManager()
    tracker = FieldTracker()
    slugify_field = "title"
    last_modified_resource.fget.short_description = _("modified")

    class Meta:
        verbose_name = _("Dataset")
        verbose_name_plural = _("Datasets")
        db_table = "dataset"
        default_manager_name = "objects"
        indexes = [
            GinIndex(fields=["i18n"]),
        ]

    def save(self, *args, **kwargs):
        """
        If the title is modified, method triggers an asynchronous task to update the
        archive symlink name associated with the dataset.
        """

        if self.pk and self.tracker.has_changed("title"):
            # if the title is modified,trigger an asynchronous task to update the
            # archive symlink name associated with the dataset.
            change_archive_symlink_name.apply_async_on_commit(
                kwargs=dict(dataset_id=self.pk, old_name=self.tracker.previous("title"))
            )
        return super().save(*args, **kwargs)


class BaseSupplement(ExtendedModel):
    name = SanitizedCharField(max_length=200, verbose_name=_("name"))
    language = SanitizedCharField(
        max_length=2,
        choices=settings.LANGUAGES,
        default=settings.LANGUAGES[0][0],
        verbose_name=_("language"),
    )
    order = models.PositiveIntegerField(verbose_name=_("order"))
    created_by = models.ForeignKey(
        User,
        models.DO_NOTHING,
        blank=False,
        editable=False,
        null=True,
        verbose_name=_("created by"),
        related_name="%(app_label)s_%(class)s_created",
    )
    modified_by = models.ForeignKey(
        User,
        models.DO_NOTHING,
        blank=False,
        editable=False,
        null=True,
        verbose_name=_("modified by"),
        related_name="%(app_label)s_%(class)s_modified",
    )
    i18n = SanitizedTranslationField(fields=("name",))

    class Meta:
        abstract = True
        ordering = ("order",)
        verbose_name = _("supplement")
        verbose_name_plural = _("supplements")

    def __str__(self):
        return self.name

    @property
    def file_size(self):
        try:
            return self.file.size
        except (FileNotFoundError, ValueError):
            return None

    @property
    def file_size_human_readable(self):
        return self.sizeof_fmt(self.file_size or 0)

    @property
    def file_size_human_readable_or_empty_str(self):
        return self.file_size_human_readable if self.file_size else ""

    @property
    def api_file_url(self):
        return self._get_api_url(self.file.url) if self.file_size else ""

    @property
    def file_url(self):
        return self._get_api_url(self.file.url) if self.file else None

    @property
    def name_csv(self):
        return f"{self.name_i18n}, {self.language.upper()}, {self.api_file_url}, {self.file_size_human_readable}"

    def save_file(self, content, filename):
        dt = self.created.date() if self.created else now().date()
        subdir = dt.isoformat().replace("-", "")
        dest_dir = os.path.join(self.file.storage.location, subdir)
        os.makedirs(dest_dir, exist_ok=True)
        file_path = os.path.join(dest_dir, filename)
        with open(file_path, "wb") as f:
            f.write(content.read())
        return "%s/%s" % (subdir, filename)


class Supplement(BaseSupplement):
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name="supplements")
    file = models.FileField(
        verbose_name=_("file"),
        storage=get_storage("datasets"),
        upload_to="%Y%m%d",
        max_length=2000,
    )

    objects = SupplementManager()


@receiver(pre_save, sender=Dataset)
def handle_dataset_pre_save(sender, instance, *args, **kwargs):
    if not instance.id:
        instance.verified = instance.created
    if instance.is_promoted and instance.status == instance.STATUS.draft:
        instance.is_promoted = False  # only published dataset can be promoted.


@receiver(post_save, sender=Dataset)
def handle_dataset_without_resources(sender, instance, *args, **kwargs):
    if not instance.resources.exists():
        Dataset.objects.filter(pk=instance.id).update(verified=instance.created)
    if instance.tracker.has_changed("organization_id"):
        organization_id = instance.tracker.previous("organization_id")
        if organization_id:
            # update ES document for previously set organization, if any.
            update_document_task.s("organizations", "Organization", organization_id).apply_async_on_commit()


@receiver(remove_related_resources, sender=Dataset)
def remove_resources_after_dataset_removed(sender, instance, *args, **kwargs):
    sender.log_debug(instance, "Remove related resources", "remove_related_resources")
    if instance.is_removed:
        for resource in instance.resources.all():
            resource.delete()

    elif instance.status == sender.STATUS.draft:
        for resource in instance.resources.all():
            resource.status = resource.STATUS.draft
            resource.save()


class DatasetTrash(Dataset, metaclass=TrashModelBase):
    class Meta:
        proxy = True
        verbose_name = _("Trash")
        verbose_name_plural = _("Trash")
        ordering = ("-modified",)


def update_related_watchers(sender, instance, *args, state=None, **kwargs):
    state = "m2m_{}".format(state)
    sender.log_debug(
        instance,
        "{} {}".format(sender._meta.object_name, state),
        "notify_{}".format(state),
        state,
    )

    update_model_watcher_task.s(
        instance.organization._meta.app_label,
        instance.organization._meta.object_name,
        instance.organization.id,
        obj_state=state,
    ).apply_async_on_commit()


core_signals.notify_published.connect(update_watcher, sender=Dataset)
core_signals.notify_restored.connect(update_watcher, sender=Dataset)
core_signals.notify_updated.connect(update_watcher, sender=Dataset)
core_signals.notify_removed.connect(update_watcher, sender=Dataset)

core_signals.notify_restored.connect(update_related_watchers, sender=Dataset)
core_signals.notify_updated.connect(update_related_watchers, sender=Dataset)
core_signals.notify_removed.connect(update_related_watchers, sender=Dataset)

core_signals.notify_published.connect(update_watcher, sender=DatasetTrash)
core_signals.notify_restored.connect(update_watcher, sender=DatasetTrash)
core_signals.notify_updated.connect(update_watcher, sender=DatasetTrash)
core_signals.notify_removed.connect(update_watcher, sender=DatasetTrash)
