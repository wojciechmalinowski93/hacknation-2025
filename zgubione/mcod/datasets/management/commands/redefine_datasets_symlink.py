import logging
from pathlib import Path
from typing import Generator, List, Optional, Set, Union

from django_tqdm import BaseCommand

from mcod.core.storages import DatasetsArchivesStorage, get_storage
from mcod.core.utils import clean_filename
from mcod.datasets.models import Dataset
from mcod.datasets.utils import create_archive_file_path

logger = logging.getLogger("mcod")


class Command(BaseCommand):
    """
    A Django management command class to update dataset symlinks in archive folders.
    Command deletes already existing symlinks in folders and creates new one
    (linked to the latest zip file).
    If argument dataset_ids is missing, scripts gets all folders in specified
    folder (archives_folder_path method - as default returns path from settings)
    for update.

    Example:
        python manage.py update_dataset_symlinks --dataset_ids 1 2 3
    """

    folder_start_name = "dataset_"
    symlinks: Optional[List[str]] = None
    dataset_id: Optional[int] = None

    def add_arguments(self, parser) -> None:
        """Add command-line arguments for the management command."""
        parser.add_argument("--dataset_ids", nargs="*", type=int, default=[], help="Dataset ids")

    def handle(self, *args, **options) -> None:
        """Main method to handle the update of dataset symlinks."""

        logger.info("Starting redefinition of datasets symlinks")

        dirs: Union[Set[Path], Generator] = self._get_folders_list(**options)
        for target_dir in dirs:
            dataset_id: Optional[int] = self.get_ds_id_from_path(folder_name=target_dir.name)

            if not target_dir.exists():
                logger.error(f"Path {target_dir} doesn't exists")
                continue

            if not dataset_id:
                logger.error(f"Folder {target_dir} doesnt match pattern 'dataset_{{id}}")
                continue

            query = Dataset.objects.filter(pk=dataset_id)

            if not query.exists():
                logger.error(f"Dataset with given id ({dataset_id}) doesnt exists.")
                continue

            dataset: Dataset = query.first()

            # Remove old symlinks
            logger.info(f"Removing symlink in dataset {dataset.pk} archive folder")
            self.remove_and_create_new_symlink(target_dir)

            # link latest zip file
            logger.info("Creating new symlink to latest archive file")
            self.create_new_symlink(dataset, str(target_dir))

    @property
    def archive_path(self) -> Path:
        """Returns archives folder location."""
        archive_storage: DatasetsArchivesStorage = get_storage(storage_name="datasets_archives")
        return Path(archive_storage.location)

    def get_ds_id_from_path(self, folder_name: str) -> Optional[int]:
        """Check whenever a given folder name is valid."""
        split_string = folder_name.split(self.folder_start_name)
        if len(split_string) == 2 and (dataset_id := split_string[-1]).isdigit:
            return int(dataset_id)

    @staticmethod
    def remove_and_create_new_symlink(dir_name: Path) -> None:
        """Check if symlinks found in specified folder, delete the object if found."""
        logger.info(f"Removing symlinks from archive folder {dir_name}")
        symlinks: List[Path] = find_symlinks_in_given_path(dir_name)
        if not symlinks:
            logger.info(f"Symlinks not found in given path {dir_name}. Nothing changed")
        for symlink in symlinks:
            remove_symlink(symlink)

    @staticmethod
    def create_new_symlink(dataset: Dataset, dir_name: str) -> None:
        """Creates a new symlink for the latest archive file."""
        target_file: Optional[Path] = get_the_latest_zip_file_or_none(Path(dir_name))
        if not target_file:
            logger.error(f"Dataset {dataset.id} doesn't have an archive zip file associated with.")
            return

        title: str = clean_filename(dataset.title)
        new_symlink_name = f"{title}.zip"
        new_symlink_path: str = dataset.archived_resources_files.field.generate_filename(dataset, new_symlink_name)

        new_symlink_name_abs_path: str = create_archive_file_path(filename=new_symlink_name, dataset=dataset)
        new_path = Path(new_symlink_name_abs_path)
        if new_path.exists():
            raise FileExistsError(f"Please be sure to remove the symlink ({new_path}) before.")
        new_path.symlink_to(target_file)
        dataset.archived_resources_files = new_symlink_path
        dataset.save()

    def _get_folders_list(self, **options) -> Union[Set[Path], Generator]:
        """Get a list of dataset folders based on command-line options."""
        if ds_ids := options.get("dataset_ids"):
            if isinstance(ds_ids, list):
                dirs = set([Path(f"{self.archive_path}/{self.folder_start_name}{ds_id}") for ds_id in ds_ids])
            else:
                dirs = {Path(f"{self.archive_path}/{self.folder_start_name}{ds_ids}")}
            return dirs
        return Path(self.archive_path).iterdir()


def find_symlinks_in_given_path(folder_path: Path) -> List[Path]:
    """Find symlinks in a given folder path."""
    return [entry for entry in folder_path.iterdir() if entry.is_symlink()]


def remove_symlink(symlink: Path) -> None:
    """Remove a symlink in a folder with given path."""
    symlink.unlink(missing_ok=True)


def get_the_latest_zip_file_or_none(dir_path: Path) -> Optional[Path]:
    """
    Get the latest zip file in a given folder.
    If file not found, returns max() function default parameter.
    """
    files = [entry for entry in dir_path.iterdir() if entry.is_file() and str(entry).endswith(".zip")]
    return max(files, key=lambda f: f.stat().st_mtime, default=None)
