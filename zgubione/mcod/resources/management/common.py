import tempfile
from pathlib import Path
from typing import List, Optional

from django.core.management import CommandError


def validate_pks(
    pks_str: Optional[str] = None,
    first_pk: Optional[int] = None,
    last_pk: Optional[int] = None,
):
    # Validate that user does not try to use `pks` with any of `first-pk` / `last-pk`
    if pks_str and any([first_pk, last_pk]):
        raise CommandError("`pks` cannot be used together with `first-pk` or `last-pk`.")

    # Validate that all pks are non-negative integers
    if pks_str:
        try:
            pks: List[int] = [int(pk) for pk in pks_str.split(",")]
        except ValueError:
            raise CommandError("`pks` must be a comma-separated list of integers.")

        negative_pks_filter = filter(lambda x: x < 0, pks)
        negative_pk = next(negative_pks_filter, None)
        if negative_pk:
            raise CommandError("All PKs in `pks` must be greater than or equal to 0.")

    # Validate that first_pk is not greater than last_pk
    if first_pk is not None and last_pk is not None and first_pk > last_pk:
        raise CommandError("`first_pk` cannot be greater than `last_pk`.")

    # Validate that first_pk is not negative
    if first_pk is not None and first_pk < 0:
        raise CommandError("`first_pk` must be greater than or equal to 0.")

    # Validate that last_pk is not negative
    if last_pk is not None and last_pk < 0:
        raise CommandError("`last_pk` must be greater than or equal to 0.")


def validate_dir_writable(dir_path: Path):
    # Check if the directory exists
    if not dir_path.exists():
        raise CommandError(f"Given directory does not exist: {dir_path}")
    # Check if the directory is writable
    try:
        with tempfile.TemporaryDirectory(dir=dir_path):
            pass
    except PermissionError:
        raise CommandError(f"Cannot write to the given directory: {dir_path}")
