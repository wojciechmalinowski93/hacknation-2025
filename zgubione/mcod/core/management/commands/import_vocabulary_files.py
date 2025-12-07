import logging
from pydoc import locate

from django.conf import settings
from django.core.management.base import BaseCommand

logger = logging.getLogger("mcod")


class Command(BaseCommand):
    help = "Import all controlled vocabulary files"

    def handle(self, *args, **options):
        logger.debug("Started controlled vocabularies import process.")
        vocabulary_sources = settings.VOCABULARY_SOURCES
        for source_name, source_settings in vocabulary_sources.items():
            if source_settings.get("enabled", True):
                try:
                    processor_class = locate(source_settings["processor_path"])
                    kwargs = source_settings["processor_kwargs"]
                    kwargs["dict_name"] = source_name
                    vocab_processor = processor_class(**kwargs)
                    logger.debug(f"Downloading file from source: {source_name}")
                    vocab_processor.download_file()
                    logger.debug(f"Processing file from source: {source_name}")
                    vocab_processor.process_file()
                    logger.debug(f"Succesfully imported vocabulary data from source: {source_name}")
                except Exception:
                    logger.exception(f"Error during vocabulary file import for source {source_name}.")
