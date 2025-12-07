import json
import logging
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

from django.conf import settings
from django.db.models import QuerySet
from marshmallow import ValidationError

from mcod.organizations.models import Organization
from mcod.reports.broken_links.serializers import BrokenLinksSerializer
from mcod.resources.models import Resource

logger = logging.getLogger("mcod")


class BrokenLinksIntermediaryJSON:
    """
    Manages an intermediary JSON file for broken link reports.

    This class handles the creation, serialization (dump), deserialization (load),
    and cleanup of a temporary JSON file. The file serves as a staging area
    for data fetched from the database before further processing.

    Each instance is associated with a unique file identified by a UUID.
    """

    _FOLDER_PATH = Path(settings.BROKEN_LINKS_CREATION_STAGING_ROOT)
    _FILE_PREFIX = "broken_links_intermediary_file__"

    def __init__(self, id_: Optional[str] = None):
        """
        Initializes the manager and sets up the path for the JSON file.

        If no id_ is provided, a new UUID4 is generated.

        Args:
            id_: An optional unique identifier for the file.
        """
        self.id: str = id_ or str(uuid.uuid4())

        # Ensure the destination directory for the JSON file exists
        self._FOLDER_PATH.mkdir(parents=True, exist_ok=True)
        self.json_path: Path = self._FOLDER_PATH / f"{self._FILE_PREFIX}{self.id}.json"

    def load(self) -> List[Dict[str, Any]]:
        """
        Loads, validates, and returns data from the JSON file.

        Raises:
            FileNotFoundError: If the JSON file does not exist.
            ValidationError: If the data in the file is not valid according
                             to the BrokenLinksSerializer.
        Returns:
            A list of dictionaries containing the validated broken links data.
        """
        try:
            with open(self.json_path, "r") as json_file:
                raw_data: List[Dict[str, Any]] = json.load(json_file)
        except FileNotFoundError:
            logger.error(f"File {self.json_path} does not exist.")
            raise
        except Exception as exc:
            logger.error(f"Failed to load file {self.json_path}: {exc}")
            raise

        errors: Dict = BrokenLinksSerializer(many=True).validate(raw_data)
        if errors:
            logger.error(f"Failed to validate broken links data: {errors}")
            raise ValidationError(errors)

        return raw_data

    def dump(self) -> None:
        """Fetches broken links data from the database and saves it to the JSON file."""
        data: List[Dict[str, Any]] = self._fetch()
        try:
            with open(self.json_path, "w") as json_file:
                json.dump(data, json_file)
        except Exception as exc:
            logger.error(f"Failed to save broken links data: {exc}")
            raise

    @staticmethod
    def _get_queryset() -> QuerySet:
        """Constructs the base queryset for fetching broken link resources."""
        qs: QuerySet = Resource.objects.with_broken_links()
        if settings.BROKEN_LINKS_EXCLUDE_DEVELOPERS:
            qs = qs.exclude(dataset__organization__institution_type=Organization.INSTITUTION_TYPE_DEVELOPER)
        qs = qs.select_related("dataset", "dataset__organization", "created_by", "modified_by")
        return qs

    def _fetch(self) -> List[Dict[str, Any]]:
        """Fetches and serializes the broken links' data."""
        qs: QuerySet = self._get_queryset()
        try:
            reports_base_data = cast(List[Dict[str, Any]], BrokenLinksSerializer(many=True).dump(qs))
        except ValidationError as exc:
            logger.error(f"Failed to fetch broken links data: {exc}")
            raise
        return reports_base_data

    def delete_old_json_files(self) -> None:
        """
        Deletes all intermediary JSON files in the folder, except for the
        one associated with this instance.
        """
        for file in self._FOLDER_PATH.iterdir():
            if file.is_file() and file.suffix == ".json" and file.name.startswith(self._FILE_PREFIX) and self.id not in file.name:
                try:
                    file.unlink()
                except Exception as exc:
                    logger.error(f"Could not remove broken links intermediary .json file: {exc}")
