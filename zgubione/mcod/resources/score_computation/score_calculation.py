import logging
from typing import Optional, Tuple

import requests
from django.conf import settings

from mcod.lib.utils import get_file_extensions_no_dot
from mcod.resources.archives import ArchiveReader, PasswordProtectedArchiveError, is_archive_file
from mcod.resources.file_validation import get_file_info
from mcod.resources.score_computation.calculators import (
    OpennessScoreCalculator,
    get_calculator_for_extension,
)
from mcod.resources.score_computation.common import (
    OpennessScoreValue,
    OptionalOpennessScoreValue,
    Source,
    SourceData,
)

logger = logging.getLogger("mcod")


def calculate_score_for_archive(source_data: SourceData) -> Tuple[Optional[OptionalOpennessScoreValue], Optional[SourceData]]:
    """Either calculates score for an archive or unpacks a single file from it for further calculations.
    See mcod.resources.file_validation.analyze_file for similar behaviour, and exceptions (geotiff/shapefiles).
    The goal is to treat singular compressed files as if they were outside the archive
    """
    if not source_data.is_archive:
        return None, source_data
    default_score: OpennessScoreValue = 1
    try:
        archive = ArchiveReader.from_bytes(source_data.data)
        with archive:
            extensions = get_file_extensions_no_dot(archive.files)
            if len(archive.files) == 1:
                # Single file - pass it down
                if source_data.extension not in settings.ARCHIVE_EXTENSIONS:
                    # prefer extension assigned by analyze_file
                    extension = source_data.extension
                else:
                    extension = extensions[0]
                extracted = archive.extract_single()
                with open(extracted, "rb") as inner_fd:
                    inner_data = inner_fd.read()
                return None, SourceData(
                    extension=extension,
                    data=inner_data,
                    res_link=source_data.res_link,
                    link_header=source_data.link_header,
                    is_archive=False,
                )
            else:
                unique_extensions = set(extensions)
                logger.debug(f"Archive contains N>1 files with {unique_extensions=} -> 1*")
                if source_data.extension not in settings.ARCHIVE_EXTENSIONS:
                    # geotiff/shapefile - multi-file archive to be sent further down
                    return None, source_data
                else:
                    return default_score, None
    except PasswordProtectedArchiveError:
        logger.exception("Encrypted archive -> openness score = 0")
        return 0, None
    except Exception as e:
        logger.exception(f"Handled exception in calculate_score_for_archive {repr(e)}")
        return default_score, None


def get_source_data(source: Source, extension: str) -> SourceData:
    """
    Returns data for a given source depending on source type (link or file).
    """
    source_data = SourceData(extension=extension)
    # when source is link
    if isinstance(source, str) and source.startswith("http"):
        try:
            response = requests.get(
                source,
                stream=True,
                allow_redirects=True,
                verify=False,
                timeout=settings.HTTP_REQUEST_DEFAULT_TIMEOUT,
            )
            source_data.res_link = source
            source_data.link_header = response.headers.get("Link")
            source_data.data = response.content
        except requests.exceptions.RequestException:
            logger.exception(f"Error while fetching source data for {source}.")
    # when source is a file
    else:
        # exc will be raised if source is str which does not start with `http`
        # - did not change due to keep current flow
        path = source.path
        _, content_type, _ = get_file_info(source.path)
        if is_archive_file(content_type):
            source_data.is_archive = True
        with open(path, "rb") as file:
            source_data.data = file.read()
    return source_data


def get_default_openness_score_for_extension(extension: str) -> OpennessScoreValue:
    """
    Returns the default openness score for a given extension based on
    `SUPPORTED_CONTENT_TYPES` list from settings.

    Note: This function returns score for FIRST extension occurrence on list.
    """
    for _, _, extensions, default_openness_score in settings.SUPPORTED_CONTENT_TYPES:
        if extension in extensions:
            return default_openness_score
    return 1


def get_score(source: Source, extension: str) -> OptionalOpennessScoreValue:
    """
    Return score for a given source and extension. This function use calculator
    for extensions with registered calculator. Returns openness score based
    on defined default scores for given extension otherwise.
    """
    source_data: SourceData = get_source_data(source, extension)
    openness_score, source_data = calculate_score_for_archive(source_data)
    if source_data is not None:
        # second pass
        calculator: Optional[OpennessScoreCalculator] = get_calculator_for_extension(source_data.extension)
        if calculator:
            openness_score = calculator(source_data)
        else:
            openness_score = get_default_openness_score_for_extension(source_data.extension)
    return openness_score
