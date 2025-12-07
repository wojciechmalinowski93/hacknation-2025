import logging
import os
import zipfile
from datetime import datetime
from pathlib import Path
from shutil import disk_usage
from typing import TYPE_CHECKING, Union

from celery_singleton import Singleton
from dateutil.relativedelta import relativedelta
from django.apps import apps
from django.conf import settings
from django.utils import translation
from sentry_sdk import set_tag

from mcod.core import storages
from mcod.core.tasks import extended_shared_task
from mcod.core.utils import CSVWriter, WriterInterface, XMLWriter, clean_filename
from mcod.datasets.utils import create_archive_file_path

if TYPE_CHECKING:
    from mcod.datasets.serializers import DatasetResourcesCSVSerializer, DatasetXMLSerializer

logger = logging.getLogger("mcod")


@extended_shared_task
def send_dataset_comment(dataset_id, comment):
    set_tag("dataset_id", str(dataset_id))
    model = apps.get_model("datasets", "Dataset")
    dataset = model.objects.get(pk=dataset_id)
    dataset.send_dataset_comment_mail(comment)
    return {"dataset": dataset_id}


def create_catalog_metadata_file(
    qs_data: list,
    schema: Union["DatasetXMLSerializer", "DatasetResourcesCSVSerializer"],
    extension: str,
    writer: WriterInterface,
):
    """
    Creates and manages catalog metadata files.

    Args:
        qs_data (List): The data to be serialized.
        schema (DatasetXMLSerializer or DatasetXMLSerializer): The schema used
        to serialize qs_data.
        extension (str): The extension for the catalog files.
        writer (WriterInterface): An instance of a class adhering to
        WriterInterface.

    This function creates catalog metadata files for multiple languages, managing
    the files for the current and previous days. It serializes the provided data
    using the given schema and writes it to the appropriate files for each language.
    Additionally, it creates symbolic links and removes old files to manage the
    catalog history.

    Note:
        - Assumes settings.LANGUAGE_CODES contains the language codes.
        - Requires settings.METADATA_MEDIA_ROOT to define the metadata media
        root path.

    Raises:
        Any exceptions related to file operations or serialization.

    """

    today = datetime.today().date()
    previous_day = today - relativedelta(days=1)

    for language in settings.LANGUAGE_CODES:
        lang_catalog_path = f"{settings.METADATA_MEDIA_ROOT}/{language}"
        previous_day_file = f"{lang_catalog_path}/katalog_{previous_day}.{extension}"
        new_file = f"{lang_catalog_path}/katalog_{today}.{extension}"
        symlink_file = f"{lang_catalog_path}/katalog.{extension}"

        if not os.path.exists(lang_catalog_path):
            os.makedirs(lang_catalog_path)

        with translation.override(language):
            data = schema.dump(qs_data)
            with open(new_file, "w") as file:
                writer.save(
                    file_object=file,
                    language_catalog_path=lang_catalog_path,
                    data=data,
                )
                logger.info(f"File {new_file} has been created")

        if os.path.exists(previous_day_file):
            os.remove(previous_day_file)

        if os.path.exists(new_file):
            if os.path.exists(symlink_file) or os.path.islink(symlink_file):
                os.remove(symlink_file)
            os.symlink(new_file, symlink_file)


@extended_shared_task
def create_csv_metadata_files() -> None:
    """Creates CSV metadata files using dataset information.

    This task is responsible for creating CSV metadata files based on dataset information.
    It fetches dataset objects with metadata fetched as a list,
    serializes them using a CSV serializer, and writes the serialized data to
    CSV files using a CSVWriter.
    """
    from mcod.datasets.serializers import DatasetResourcesCSVSerializer

    dataset_model = apps.get_model("datasets", "Dataset")
    qs_data = dataset_model.objects.with_metadata_fetched_as_list()

    logger.info("Started task: create_csv_metadata_files")
    csv_schema = DatasetResourcesCSVSerializer(many=True)
    csv_writer: CSVWriter = CSVWriter(
        headers=csv_schema.get_csv_headers(),
    )

    create_catalog_metadata_file(qs_data, csv_schema, "csv", writer=csv_writer)


@extended_shared_task
def create_xml_metadata_files() -> None:
    """Creates XML metadata files using dataset information.

    This task is responsible for creating XML metadata files based on dataset information.
    It fetches dataset objects with metadata fetched as a list, serializes them using an
    XML serializer, and writes the serialized data to XML files using an XMLWriter.
    """

    from mcod.datasets.serializers import DatasetXMLWriterSerializer

    dataset_model = apps.get_model("datasets", "Dataset")
    qs_data: list = dataset_model.objects.with_metadata_fetched_as_list()

    logger.info("Started task: create_xml_metadata_files")
    xml_schema = DatasetXMLWriterSerializer(many=True)
    xml_writer: XMLWriter = XMLWriter()

    create_catalog_metadata_file(qs_data, xml_schema, "xml", writer=xml_writer)


@extended_shared_task
def send_dataset_update_reminder():
    logger.debug("Attempting to send datasets update reminders.")
    dataset_model = apps.get_model("datasets", "Dataset")
    ds_to_notify = dataset_model.objects.datasets_to_notify()
    logger.debug(f"Found {len(ds_to_notify)} datasets.")
    sent_messages = dataset_model.send_dataset_update_reminder_mails(ds_to_notify)
    logger.debug(f"Sent {sent_messages} messages with dataset update reminder.")


@extended_shared_task(base=Singleton)
def change_archive_symlink_name(dataset_id: int, old_name: str) -> None:
    """
    Change the name of the symbolic link for the archive of a dataset identified
    by 'dataset_id'.

    Args:
    - dataset_id (int): The ID of the dataset for which the archive symlink
    name needs to be changed.
    - old_name (str): The current name of the symbolic link to be updated.

    Description:
    This function updates the symbolic link name associated with the archive
    of a dataset. It retrieves the dataset using the provided 'dataset_id',
    constructs the paths for both the old and new symbolic link names, checks if the
    old symbolic link exists, unlinks it, and creates a new symbolic link
    with the updated name. Finally, it updates the dataset's 'archived_resources_files'
    field with the new symlink path.
    """
    logger.info("Starting archive symlink name change.")
    set_tag("dataset_id", str(dataset_id))
    dataset_model = apps.get_model("datasets", "Dataset")
    dataset = dataset_model.raw.get(pk=dataset_id)
    title: str = clean_filename(dataset.title)
    old_title: str = clean_filename(old_name)

    old_symlink_name = f"{old_title}.zip"
    new_symlink_name = f"{title}.zip"
    new_symlink_path: str = dataset.archived_resources_files.field.generate_filename(dataset, new_symlink_name)

    old_symlink_absolute_path: str = create_archive_file_path(filename=old_symlink_name, dataset=dataset)
    new_symlink_name_abs_path: str = create_archive_file_path(filename=new_symlink_name, dataset=dataset)
    logger.info(f"Symlink abs path: {old_symlink_absolute_path}")

    if (symlink := Path(old_symlink_absolute_path)).is_symlink():
        target: Path = symlink.resolve()
        new_path = Path(new_symlink_name_abs_path)
        symlink.unlink()
        new_path.symlink_to(target)

        logger.info(f"Symlink renamed to: {new_symlink_name}")
        dataset.archived_resources_files = new_symlink_path
        dataset.save()
    else:
        logger.error(f"Unfortunately, symlink {old_symlink_absolute_path} does not exist")


#  FIXME: lremkowicz: remove noqa C901 comment after removing
#  S61_fix_for_dataset_rename_symlink_archive_problem.be flag
@extended_shared_task(base=Singleton)
def archive_resources_files(dataset_id: int):  # noqa: C901
    logger.info("Starting archive_resources_files task.")
    set_tag("dataset_id", str(dataset_id))
    free_space = disk_usage(settings.MEDIA_ROOT).free
    if free_space < settings.ALLOWED_MINIMUM_SPACE:
        logger.error("There is not enough free space on disk, archive creation is canceled.")
        raise ResourceWarning
    logger.debug(f"Updating dataset resources files archive for dataset {dataset_id}")
    dataset_model = apps.get_model("datasets", "Dataset")
    ds = dataset_model.raw.get(pk=dataset_id)

    def create_full_file_path(_fname):
        storage_location = ds.archived_resources_files.storage.location
        full_fname = ds.archived_resources_files.field.generate_filename(ds, _fname)
        return os.path.join(storage_location, full_fname)

    creation_start = datetime.now()
    dataset_title = clean_filename(ds.title)
    tmp_filename = f'{dataset_title}_{creation_start.strftime("%Y-%m-%d-%H%M%S%f")}.zip'
    symlink_name = f"{dataset_title}.zip"
    res_storage = storages.get_storage("resources")
    full_symlink_name = ds.archived_resources_files.field.generate_filename(ds, symlink_name)
    full_file_path = create_full_file_path(tmp_filename)
    full_symlink_path = create_full_file_path(symlink_name)
    full_tmp_symlink_path = create_full_file_path("tmp_resources_files.zip")
    abs_path = os.path.dirname(full_file_path)
    os.makedirs(abs_path, exist_ok=True)
    files_details = ds.resources_files_list
    log_msg = f"Updated dataset {dataset_id} archive with {tmp_filename}"
    skipped_files = 0
    with zipfile.ZipFile(full_file_path, "w", zipfile.ZIP_DEFLATED, compresslevel=1) as main_zip:
        res_location = res_storage.location
        for file_details in files_details:
            split_name = file_details[0].split("/")
            full_path = os.path.join(res_location, file_details[0])
            try:
                res_title = clean_filename(file_details[2])
                main_zip.write(
                    full_path,
                    os.path.join(f"{res_title}_{file_details[1]}", split_name[1]),
                )
            except FileNotFoundError:
                skipped_files += 1
                logger.debug("Couldn't find file {} for resource with id {}, skipping.".format(full_path, file_details[1]))
    no_archived_files = skipped_files == len(files_details)

    if no_archived_files:
        os.remove(full_file_path)
        log_msg = f"No files archived for dataset with id {dataset_id}, archive not updated."
    elif not ds.archived_resources_files and not no_archived_files:
        os.symlink(full_file_path, full_symlink_path)
        dataset_model.objects.filter(pk=dataset_id).update(archived_resources_files=full_symlink_name)
    elif ds.archived_resources_files and not no_archived_files:
        os.symlink(full_file_path, full_tmp_symlink_path)
        os.rename(full_tmp_symlink_path, full_symlink_path)
    if ds.archived_resources_files and no_archived_files:
        old_file_path = os.path.realpath(full_symlink_path)
        dataset_model.objects.filter(pk=dataset_id).update(archived_resources_files=None)
        os.remove(full_symlink_path)
        os.remove(old_file_path)
        log_msg = f"Removed archive {old_file_path} from dataset {dataset_id}"
    logger.debug(log_msg)
