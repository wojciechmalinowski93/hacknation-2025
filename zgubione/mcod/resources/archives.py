import logging
import os
import tempfile
import zipfile
from pathlib import Path
from typing import IO, BinaryIO, Iterator, Literal, Tuple, Union

import libarchive
import magic
import py7zr
import rarfile
from mimeparse import parse_mime_type

from mcod import settings

logger = logging.getLogger("mcod")


class UnsupportedArchiveError(Exception):
    pass


def is_archive_file(content_type: str) -> bool:
    return content_type in settings.ARCHIVE_CONTENT_TYPES


def _is_password_protected_7z(source: BinaryIO) -> bool:
    if not py7zr.is_7zfile(source):
        return False
    try:
        with py7zr.SevenZipFile(source) as file:
            return file.needs_password()
    except py7zr.PasswordRequired:
        return True


def _is_password_protected_zip(source: BinaryIO) -> bool:
    try:
        with zipfile.ZipFile(source) as zip_file:
            for zinfo in zip_file.filelist:
                is_encrypted = zinfo.flag_bits & 0x1
                if is_encrypted:
                    return True
    except zipfile.BadZipFile:
        pass
    return False


def _is_password_protected_rar(source: BinaryIO) -> bool:
    if not rarfile.is_rarfile(source):
        return False
    try:
        with rarfile.RarFile(source) as file:
            return file.needs_password()
    except rarfile.PasswordRequired:
        return True


def get_memory_file_info(file: IO) -> Tuple[str, str, dict]:
    _magic = magic.Magic(mime=True, mime_encoding=True)
    result = _magic.from_buffer(file.read(1024))
    file.seek(0)
    return parse_mime_type(result)


def is_password_protected_archive_file(file: BinaryIO) -> bool:
    family, content_type, options = get_memory_file_info(file)
    content_type_2_func = {
        **{ct: _is_password_protected_rar for ct in settings.ARCHIVE_RAR_CONTENT_TYPES},
        **{ct: _is_password_protected_7z for ct in settings.ARCHIVE_7Z_CONTENT_TYPES},
        **{ct: _is_password_protected_zip for ct in settings.ARCHIVE_ZIP_CONTENT_TYPES},
    }
    if content_type not in content_type_2_func:
        return False

    return content_type_2_func[content_type](file)


class ArchiveReader:
    format: Literal["rar", "other"]

    def __init__(self, source: Union[str, Path]):
        self.files: Tuple[Union[Path, str], ...] = ()
        self._source_file = Path(source)
        self._rar = None
        if not self._source_file.exists():
            raise ValueError(f"File {self._source_file} does not exist")
        with open(self._source_file, "rb") as fd:
            if is_password_protected_archive_file(fd):
                raise PasswordProtectedArchiveError
        self.root_dir = tempfile.TemporaryDirectory()
        if rarfile.is_rarfile(self._source_file):
            _rar_archive = rarfile.RarFile(self._source_file)
            self.files = tuple([f.filename for f in _rar_archive.infolist() if f.is_file()])
            self._rar = _rar_archive
        else:
            files = []
            with libarchive.file_reader(str(self._source_file)) as archive:
                for entry in archive:
                    if entry.isfile:
                        files.append(entry.path)
            self.files = tuple(files)

    @classmethod
    def from_bytes(cls, b: bytes) -> "ArchiveReader":
        _, tmp_file_path = tempfile.mkstemp()
        with open(tmp_file_path, "wb") as fd:
            fd.write(b)
        archive = ArchiveReader(tmp_file_path)
        return archive

    def __len__(self):
        return len(self.files)

    def __getitem__(self, item: int) -> str:
        return self.files[item]

    def __enter__(self):
        return self

    def __iter__(self) -> Iterator[str]:
        return iter(self.files)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.root_dir.cleanup()
        if self._rar:
            self._rar.__exit__(exc_type, exc_val, exc_tb)

    def get_by_extension(self, extension: str) -> Iterator[Path]:
        extension = extension[1:] if extension.startswith(".") else extension
        for f in self.files:
            if f.endswith(f".{extension}"):
                extracted_path = self.extract(f)
                yield extracted_path

    def extract(self, path_in_archive: str) -> Path:
        if path_in_archive not in self.files:
            raise KeyError(path_in_archive)
        target = os.path.join(self.root_dir.name, path_in_archive)
        target_dir = os.path.dirname(target)
        os.makedirs(target_dir, exist_ok=True)
        if self._rar:
            for f in self._rar.infolist():
                if f.filename == path_in_archive:
                    self._rar.extract(f, target_dir)
        else:
            with libarchive.file_reader(str(self._source_file)) as archive:
                for entry in archive:
                    if entry.isfile:
                        if entry.path == path_in_archive:
                            with open(target, "wb") as f:
                                for block in entry.get_blocks():
                                    f.write(block)
        return Path(target)

    def extract_single(self) -> Path:
        if len(self.files) != 1:
            raise KeyError(0)
        path_in_archive = self.files[0]
        return self.extract(path_in_archive)

    def __repr__(self) -> str:
        files_ = ", ".join(self.files[:4])
        if len(self.files) > 4:
            files_ += ", ..."
        return f"ArchiveReader({self._source_file.name})[{files_}]"

    __str__ = __repr__


class PasswordProtectedArchiveError(Exception):
    pass
