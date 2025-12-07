import logging
import os

from django.apps import apps
from django.db.models import Sum

from mcod import settings
from mcod.core.tasks import extended_shared_task
from mcod.counters.lib import Counter

logger = logging.getLogger("kibana-statistics")


def get_directory_size(startpath):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(startpath):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    return total_size


@extended_shared_task
def save_counters():
    counter = Counter()
    counter.save_counters()
    return {}


@extended_shared_task
def kibana_statistics():
    download_counter_model = apps.get_model("counters.ResourceDownloadCounter")
    view_counter_model = apps.get_model("counters.ResourceViewCounter")
    resource_model = apps.get_model("resources.Resource")
    resources = resource_model.objects.filter(status="published")
    organization_model = apps.get_model("organizations.Organization")
    organizations_with_dataset = organization_model.objects.filter(datasets__status="published").distinct()
    institution_type_private = organization_model.INSTITUTION_TYPE_PRIVATE

    public_organizations_with_dataset = organizations_with_dataset.exclude(institution_type=institution_type_private)
    resources_of_public_organizations = resources.exclude(dataset__organization__institution_type=institution_type_private)
    public_downloads_count = (
        download_counter_model.objects.filter(resource__in=resources_of_public_organizations).aggregate(Sum("count"))[
            "count__sum"
        ]
        or 0
    )
    public_views_count = (
        view_counter_model.objects.filter(resource__in=resources_of_public_organizations).aggregate(Sum("count"))["count__sum"]
        or 0
    )
    size_of_documents_of_public_organizations = sum(
        resource.file.size
        for resource in resources_of_public_organizations.iterator()
        if resource.file and resource.file.storage.exists(resource.file.path)
    )

    private_organizations_with_dataset = organizations_with_dataset.filter(institution_type=institution_type_private)
    resources_of_private_organizations = resources.filter(dataset__organization__institution_type=institution_type_private)
    private_downloads_count = (
        download_counter_model.objects.filter(resource__in=resources_of_private_organizations).aggregate(Sum("count"))[
            "count__sum"
        ]
        or 0
    )
    private_views_count = (
        view_counter_model.objects.filter(resource__in=resources_of_private_organizations).aggregate(Sum("count"))["count__sum"]
        or 0
    )
    size_of_documents_of_private_organizations = sum(
        resource.file.size
        for resource in resources_of_private_organizations.iterator()
        if resource.file and resource.file.storage.exists(resource.file.path)
    )

    size_of_media_resources = get_directory_size(settings.RESOURCES_MEDIA_ROOT)

    logger.info(
        "public_organizations_with_dataset %d",
        public_organizations_with_dataset.count(),
    )
    logger.info(
        "resources_of_public_organizations %d",
        resources_of_public_organizations.count(),
    )
    logger.info("downloads_of_documents_of_public_organizations %d", public_downloads_count)
    logger.info("views_of_documents_of_public_organizations %d", public_views_count)
    logger.info(
        "size_of_documents_of_public_organizations %d",
        size_of_documents_of_public_organizations,
    )

    logger.info(
        "private_organizations_with_dataset %d",
        private_organizations_with_dataset.count(),
    )
    logger.info(
        "resources_of_private_organizations %d",
        resources_of_private_organizations.count(),
    )
    logger.info("downloads_of_documents_of_private_organizations %d", private_downloads_count)
    logger.info("views_of_documents_of_private_organizations %d", private_views_count)
    logger.info(
        "size_of_documents_of_private_organizations %d",
        size_of_documents_of_private_organizations,
    )

    logger.info("size_of_media_resources %d", size_of_media_resources)
    return {}
