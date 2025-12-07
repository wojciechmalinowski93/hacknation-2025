import logging
import time

from celery_progress.backend import ProgressRecorder
from django.apps import apps
from django.utils.translation import gettext_lazy as _
from sentry_sdk import set_tag

from mcod.core.tasks import extended_shared_task
from mcod.harvester.utils import (
    check_content_type,
    check_xml_filename,
    get_remote_xml_hash,
    get_xml_headers,
    retrieve_to_file,
    validate_md5,
    validate_xml,
)

logger = logging.getLogger("mcod")


@extended_shared_task
def import_data_task(data_source_id, force=False):
    set_tag("data_source_id", str(data_source_id))
    DataSource = apps.get_model("harvester.DataSource")
    obj = DataSource.objects.active().filter(id=data_source_id).first()
    if obj and (obj.import_needed() or force):
        obj.import_data()
    return {}


@extended_shared_task
def harvester_supervisor():
    DataSource = apps.get_model("harvester.DataSource")
    for obj in DataSource.objects.active():
        if obj.import_needed():
            logger.debug(f"import from {obj}")
            import_data_task.s(obj.id).apply_async()
    return {}


@extended_shared_task(bind=True, ignore_result=False)
def validate_xml_url_task(self, url):
    progress_recorder = ProgressRecorder(self)

    check_xml_filename(url)
    time.sleep(1)
    progress_recorder.set_progress(1, 7, description=_("Checking of file name"))

    html_headers = get_xml_headers(url)
    time.sleep(1)
    progress_recorder.set_progress(2, 7, description=_("Fetching of HTTP headers"))

    check_content_type(html_headers)
    time.sleep(1)
    progress_recorder.set_progress(3, 7, description=_("Checking of content type"))

    remote_hash_url, remote_hash = get_remote_xml_hash(url)
    time.sleep(1)
    progress_recorder.set_progress(4, 7, description=_("Checking of MD5 file"))

    filename, headers = retrieve_to_file(url)
    time.sleep(1)
    progress_recorder.set_progress(5, 7, description=_("Downloading of xml file"))

    source_hash = validate_md5(filename, remote_hash)
    time.sleep(1)
    progress_recorder.set_progress(6, 7, description=_("Validation of MD5"))

    validate_xml(filename)
    time.sleep(1)
    progress_recorder.set_progress(7, 7, description=_("Validation of xml file"))

    time.sleep(1)
    if source_hash:
        return {"source_hash": source_hash}
    return {}
