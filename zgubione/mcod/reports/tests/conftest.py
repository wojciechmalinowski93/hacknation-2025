import shutil
from pathlib import Path
from typing import Dict, Tuple

import pytest
from django.conf import settings

from mcod.core.tests.fixtures import *  # noqa
from mcod.reports.broken_links.constants import ReportFormat, ReportLanguage


@pytest.fixture
def reports_media_root(monkeypatch, tmp_path) -> str:
    from django.conf import settings

    monkeypatch.setattr(settings, "REPORTS_MEDIA_ROOT", str(tmp_path))
    return settings.REPORTS_MEDIA_ROOT


@pytest.fixture
def sample_public_broken_links_files(
    reports_media_root: Path,
) -> Dict[Tuple[ReportLanguage, ReportFormat], Path]:

    test_samples_root_path: Path = Path(settings.TEST_SAMPLES_PATH)
    sample_pl_csv: Path = test_samples_root_path / "sample_public_broken_links_report_PL.csv"
    sample_pl_xlsx: Path = test_samples_root_path / "sample_public_broken_links_report_PL.xlsx"
    sample_en_csv: Path = test_samples_root_path / "sample_public_broken_links_report_EN.csv"
    sample_en_xlsx: Path = test_samples_root_path / "sample_public_broken_links_report_EN.xlsx"

    # Public report directory path for both languages.
    pl_path: Path = Path(reports_media_root, "resources", "public", "pl")
    pl_path.mkdir(parents=True, exist_ok=True)
    en_path: Path = Path(reports_media_root, "resources", "public", "en")
    en_path.mkdir(parents=True, exist_ok=True)

    # Prepare files paths for all languages and extensions.
    pl_csv_file: Path = pl_path.joinpath("file_pl.csv")
    pl_xlsx_file: Path = pl_path.joinpath("file_pl.xlsx")
    en_csv_file: Path = en_path.joinpath("file_en.csv")
    en_xlsx_file: Path = en_path.joinpath("file_en.xlsx")

    # Copy samples file.
    shutil.copy(sample_pl_csv, pl_csv_file)
    shutil.copy(sample_pl_xlsx, pl_xlsx_file)
    shutil.copy(sample_en_csv, en_csv_file)
    shutil.copy(sample_en_xlsx, en_xlsx_file)

    return {
        (ReportLanguage.PL, ReportFormat.CSV): pl_csv_file,
        (ReportLanguage.PL, ReportFormat.XLSX): pl_xlsx_file,
        (ReportLanguage.EN, ReportFormat.CSV): en_csv_file,
        (ReportLanguage.EN, ReportFormat.XLSX): en_xlsx_file,
    }
