import os
from datetime import datetime

from django.conf import settings
from django.core.files.storage import FileSystemStorage


class BaseFileSystemStorage(FileSystemStorage):
    def __init__(self, location=None, base_url=None, **kwargs):
        location = location or settings.MEDIA_ROOT
        base_url = base_url or settings.MEDIA_URL

        if not os.path.exists(location):
            os.makedirs(location)

        super().__init__(location, base_url, **kwargs)

    def name_from_url(self, url):
        if url:
            name = url.replace(self.base_url, "")
            if self.exists(name):
                return name
        return None


class ResourcesStorage(BaseFileSystemStorage):
    def __init__(self, location=None, base_url=None, **kwargs):
        location = location or settings.RESOURCES_MEDIA_ROOT
        base_url = base_url or "%s" % settings.RESOURCES_URL
        super().__init__(location=location, base_url=base_url, **kwargs)


class WaitingResourcesStorage(BaseFileSystemStorage):
    def __init__(self, location=None, base_url=None, **kwargs):
        location = location or os.path.join(settings.RESOURCES_MEDIA_ROOT, "waiting")
        base_url = base_url or "%s/%s" % (settings.RESOURCES_URL, "waiting")
        super().__init__(location=location, base_url=base_url, **kwargs)


class ApplicationImagesStorage(BaseFileSystemStorage):
    def __init__(self, location=None, base_url=None, **kwargs):
        location = location or os.path.join(settings.IMAGES_MEDIA_ROOT, "applications")
        base_url = base_url or "%s/%s" % (settings.IMAGES_URL, "applications")
        super().__init__(location=location, base_url=base_url, **kwargs)


class CourseStorage(BaseFileSystemStorage):
    def __init__(self, location=None, base_url=None, **kwargs):
        location = location or os.path.join(settings.ACADEMY_MEDIA_ROOT, "courses")
        base_url = base_url or "%s/%s" % (settings.ACADEMY_URL, "courses")
        super().__init__(location=location, base_url=base_url, **kwargs)


class CourseMaterialsStorage(BaseFileSystemStorage):
    def __init__(self, location=None, base_url=None, **kwargs):
        location = location or os.path.join(settings.ACADEMY_MEDIA_ROOT, "courses_materials")
        base_url = base_url or "%s/%s" % (settings.ACADEMY_URL, "courses_materials")
        super().__init__(location=location, base_url=base_url, **kwargs)


class OrganizationImagesStorage(BaseFileSystemStorage):
    def __init__(self, location=None, base_url=None, **kwargs):
        location = location or os.path.join(settings.IMAGES_MEDIA_ROOT, "organizations")
        base_url = base_url or "%s/%s" % (settings.IMAGES_URL, "organizations")
        super().__init__(location=location, base_url=base_url, **kwargs)


class CommonStorage(BaseFileSystemStorage):
    def __init__(self, location=None, base_url=None, **kwargs):
        location = location or os.path.join(settings.IMAGES_MEDIA_ROOT, "common")
        base_url = base_url or "%s/%s" % (settings.IMAGES_URL, "common")
        super().__init__(location=location, base_url=base_url, **kwargs)


class NewsletterStorage(BaseFileSystemStorage):
    def __init__(self, location=None, base_url=None, **kwargs):
        location = location or settings.NEWSLETTER_MEDIA_ROOT
        base_url = base_url or settings.NEWSLETTER_URL
        super().__init__(location=location, base_url=base_url, **kwargs)


class LaboratoryStorage(BaseFileSystemStorage):
    def __init__(self, location=None, base_url=None, **kwargs):
        location = location or os.path.join(settings.LABORATORY_MEDIA_ROOT, "lab_reports")
        base_url = base_url or "%s/%s" % (settings.LABORATORY_URL, "lab_reports")
        super().__init__(location=location, base_url=base_url, **kwargs)


class MeetingStorage(BaseFileSystemStorage):
    def __init__(self, location=None, base_url=None, **kwargs):
        location = location or os.path.join(settings.MEETINGS_MEDIA_ROOT, "meetings")
        base_url = base_url or "%s/%s" % (settings.MEETINGS_URL, "meetings")
        super().__init__(location=location, base_url=base_url, **kwargs)


class DatasetsImagesStorage(BaseFileSystemStorage):
    def __init__(self, location=None, base_url=None, **kwargs):
        location = location or os.path.join(settings.IMAGES_MEDIA_ROOT, "datasets")
        base_url = base_url or "%s/%s" % (settings.IMAGES_URL, "datasets")
        super().__init__(location=location, base_url=base_url, **kwargs)


class DatasetsArchivesStorage(BaseFileSystemStorage):
    def __init__(self, location=None, base_url=None, **kwargs):
        archives_path = os.path.join(settings.DATASETS_MEDIA_ROOT, "archives")
        location = location or archives_path
        base_url = base_url or "%s/%s" % (settings.DATASETS_URL, "archives")
        super().__init__(location=location, base_url=base_url, **kwargs)


class DCATVocabulariesStorage(BaseFileSystemStorage):

    def __init__(self, location=None, base_url=None, **kwargs):
        location = location or settings.DCAT_VOCABULARIES_MEDIA_ROOT
        base_url = base_url or "%s" % settings.DCAT_VOCABULARIES_URL
        super().__init__(location=location, base_url=base_url, **kwargs)

    def get_available_name(self, name, max_length=None):
        full_name = self.path(name)
        dirname, file_name = os.path.split(full_name)
        file_root, file_ext = os.path.splitext(file_name)
        now = datetime.now()
        new_file_name = f"{file_root}_{now:%Y%m%d_%H%M%S}{file_ext}"
        try:
            os.rename(full_name, os.path.join(dirname, new_file_name))
        except FileNotFoundError:
            pass
        return name


class ChartThumbsStorage(BaseFileSystemStorage):
    def __init__(self, location=None, base_url=None, **kwargs):
        location = location or os.path.join(settings.IMAGES_MEDIA_ROOT, "stats")
        base_url = base_url or "%s/%s" % (settings.IMAGES_URL, "stats")
        super().__init__(location=location, base_url=base_url, **kwargs)


class ShowcasesStorage(BaseFileSystemStorage):
    def __init__(self, location=None, base_url=None, **kwargs):
        location = location or settings.SHOWCASES_MEDIA_ROOT
        base_url = base_url or "%s" % settings.SHOWCASES_URL
        super().__init__(location=location, base_url=base_url, **kwargs)


AVAILABLE_STORAGES = {
    "applications": ApplicationImagesStorage,
    "organizations": OrganizationImagesStorage,
    "resources": ResourcesStorage,
    "waiting_resources": WaitingResourcesStorage,
    "common": CommonStorage,
    "newsletter": NewsletterStorage,
    "courses": CourseStorage,
    "courses_materials": CourseMaterialsStorage,
    "lab_reports": LaboratoryStorage,
    "meetings": MeetingStorage,
    "datasets": DatasetsImagesStorage,
    "datasets_archives": DatasetsArchivesStorage,
    "dcat_vocabularies": DCATVocabulariesStorage,
    "chart_thumbs": ChartThumbsStorage,
    "showcases": ShowcasesStorage,
}


def get_storage(storage_name, location=None, base_url=None):
    storage_name = storage_name or "images"
    try:
        cls_storage = AVAILABLE_STORAGES[storage_name]
    except KeyError:
        cls_storage = BaseFileSystemStorage
    return cls_storage(location=location, base_url=base_url)
