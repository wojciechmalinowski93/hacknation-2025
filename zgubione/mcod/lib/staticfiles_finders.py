import os

from django.conf import settings
from django.contrib.staticfiles import utils
from django.contrib.staticfiles.finders import BaseFinder
from django.core.files.storage import FileSystemStorage
from django.utils._os import safe_join


class StaticRootFinder(BaseFinder):
    """
    A static files finder that uses the ``STATIC_ROOT`` setting
    to locate files.
    """

    def __init__(self, app_names=None, *args, **kwargs):
        # List of locations with static files
        self.location = settings.STATIC_ROOT
        self.storage = FileSystemStorage(location=self.location)
        super().__init__(*args, **kwargs)

    def check(self, **kwargs):
        # TODO: check if directory exist
        errors = []
        return errors

    def find(self, path, all=False):
        """
        Look for files in the extra locations as defined in STATICFILES_DIRS.
        """
        matches = []
        matched_path = self.find_location(self.location, path)
        if matched_path:
            if not all:
                return matched_path
                matches.append(matched_path)
        return matches

    def find_location(self, root, path, prefix=None):
        """
        Find a requested static file in a location and return the found
        absolute path (or ``None`` if no match).
        """
        if prefix:
            prefix = "%s%s" % (prefix, os.sep)
            if not path.startswith(prefix):
                return None
            path = path[len(prefix) :]
        path = safe_join(root, path)
        if os.path.exists(path):
            return path

    def list(self, ignore_patterns):
        """
        List all files in all locations.
        """
        for path in utils.get_files(self.storage, ignore_patterns):
            yield path, self.storage
