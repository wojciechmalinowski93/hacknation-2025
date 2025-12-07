import os
from typing import TYPE_CHECKING

from mcod import settings

if TYPE_CHECKING:
    from mcod.datasets.models import Dataset


def _batch_qs(qs):
    batch_size = settings.CSV_CATALOG_BATCH_SIZE
    total = qs.count()
    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        yield start, end, total, qs[start:end]


def create_archive_file_path(filename: str, dataset: "Dataset") -> str:
    """
    Create the full path for an archive file given its filename and dataset.

    Args:
    - filename (str): The name of the archive file.
    - dataset (Dataset): The dataset object associated with the archive file.

    Returns:
    - str: The full path of the archive file.

    Description:
    This function generates the complete file path for an archive file based on
    the provided 'filename' and 'dataset'. It uses the storage location of the dataset's
    archived resources files and the filename to construct the full path.
    """
    storage_location = dataset.archived_resources_files.storage.location
    full_file_name = dataset.archived_resources_files.field.generate_filename(dataset, filename)
    return str(os.path.join(storage_location, full_file_name))
