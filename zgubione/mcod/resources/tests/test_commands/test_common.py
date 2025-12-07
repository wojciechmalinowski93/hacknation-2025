from typing import Optional
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import CommandError

from mcod.resources.management.common import validate_dir_writable, validate_pks


@pytest.fixture
def mock_not_existing_path() -> MagicMock:
    path = MagicMock()
    path.exists.return_value = False
    yield path


@pytest.fixture
def mock_existing_path() -> MagicMock:
    path = MagicMock()
    path.exists.return_value = True
    yield path


@pytest.fixture
def mock_temp_dir() -> MagicMock:
    with patch("mcod.resources.management.common.tempfile.TemporaryDirectory") as mock_temp_dir:
        yield mock_temp_dir


class TestValidationCommandArguments:
    @pytest.mark.parametrize(
        "first_pk, last_pk, pks_str",
        [
            (100, 0, None),
            (200, 100, None),
            (-100, 100, None),
            (0, -100, None),
            (-100, 0, None),
            (-100, None, None),
            (None, -100, None),
            (None, None, "text"),
            (None, None, "text,comma,sep"),
            (None, None, "1,and,text,2"),
            (None, None, "1,2,-3"),
        ],
    )
    def test__validate_pks_raise_command_error(
        self,
        first_pk: Optional[int],
        last_pk: Optional[int],
        pks_str: Optional[str],
    ):
        with pytest.raises(CommandError):
            validate_pks(pks_str=pks_str, first_pk=first_pk, last_pk=last_pk)

    @pytest.mark.parametrize(
        "first_pk, last_pk, pks_str",
        [
            (0, 100, None),
            (0, 100, ""),
            (100, 100, ""),
            (100, None, ""),
            (None, 100, ""),
            (None, None, "1,2,3,100"),
        ],
    )
    def test__validate_pks_ok(
        self,
        first_pk: Optional[int],
        last_pk: Optional[int],
        pks_str: Optional[str],
    ):
        validate_pks(pks_str=pks_str, first_pk=first_pk, last_pk=last_pk)

    def test_validate_dir_writable_when_path_does_not_exist(
        self,
        mock_not_existing_path: MagicMock,
    ):
        with pytest.raises(CommandError):
            validate_dir_writable(mock_not_existing_path)

        assert mock_not_existing_path.exists.call_count == 1

    def test_validate_dir_writable_when_path_exist_but_not_writable(
        self,
        mock_existing_path: MagicMock,
        mock_temp_dir: MagicMock,
    ):
        mock_temp_dir.side_effect = PermissionError
        with pytest.raises(CommandError):
            validate_dir_writable(mock_existing_path)

        assert mock_existing_path.exists.call_count == 1
        assert mock_temp_dir.called == 1

    def test_validate_dir_writable(
        self,
        mock_existing_path: MagicMock,
        mock_temp_dir: MagicMock,
    ):
        validate_dir_writable(mock_existing_path)
        assert mock_existing_path.exists.call_count == 1
        assert mock_temp_dir.called == 1
