from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from dateutil.relativedelta import relativedelta
from django.core import mail
from django.test import override_settings
from pytest_bdd import scenarios
from pytest_mock import MockerFixture

from mcod.datasets.tasks import (
    create_csv_metadata_files,
    create_xml_metadata_files,
    send_dataset_update_reminder,
)

scenarios("features/dataset_send_update_reminder.feature")


class TestDatasetUpdateReminder:
    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    @pytest.mark.parametrize(
        "update_freq, date_delay, reldelta",
        [
            ("weekly", 1, relativedelta(days=7)),
            ("monthly", 3, relativedelta(months=1)),
            ("quarterly", 7, relativedelta(months=3)),
            ("everyHalfYear", 7, relativedelta(months=6)),
            ("yearly", 7, relativedelta(years=1)),
        ],
    )
    def test_update_reminder_is_sent(self, update_freq, date_delay, reldelta, dataset_with_resource, admin):
        ds = dataset_with_resource
        ds.title = "Test wysyłki notyfikacji dot. aktualizacji zbioru"
        ds.update_frequency = update_freq
        ds.modified_by = admin
        ds.save()
        first_res = ds.resources.all()[0]
        first_res.data_date = date.today() + relativedelta(days=date_delay) - reldelta
        first_res.type = "file"
        first_res.save()
        send_dataset_update_reminder()
        assert len(mail.outbox) == 1
        assert mail.outbox[0].subject == "Test wysyłki notyfikacji dot. aktualizacji zbioru"
        assert "Przypomnienie o aktualizacji Zbioru danych" in mail.outbox[0].body
        assert mail.outbox[0].to == [admin.email]

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    @pytest.mark.parametrize(
        "res_type, update_freq, date_delay, reldelta, notification_enabled",
        [
            ("api", "weekly", 1, relativedelta(days=7), True),
            ("website", "monthly", 3, relativedelta(months=1), True),
            ("file", "monthly", 3, relativedelta(months=1), False),
            ("file", "notApplicable", 3, relativedelta(months=1), True),
            ("file", "daily", 3, relativedelta(months=1), True),
        ],
    )
    def test_update_reminder_is_not_sent(
        self,
        res_type,
        update_freq,
        date_delay,
        reldelta,
        notification_enabled,
        dataset_with_resource,
        admin,
    ):
        ds = dataset_with_resource
        ds.update_frequency = update_freq
        ds.modified_by = admin
        ds.is_update_notification_enabled = notification_enabled
        ds.save()
        first_res = ds.resources.all()[0]
        first_res.data_date = date.today() + relativedelta(days=date_delay) - reldelta
        first_res.type = res_type
        first_res.save()
        send_dataset_update_reminder()
        assert len(mail.outbox) == 0

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_update_reminder_sent_to_notification_recipient_if_set(self, dataset_with_resource, admin):
        ds = dataset_with_resource
        ds.title = "Test wysyłki notyfikacji dot. aktualizacji zbioru"
        ds.update_frequency = "weekly"
        ds.modified_by = admin
        ds.update_notification_recipient_email = "test-recipient@test.com"
        ds.save()
        first_res = ds.resources.all()[0]
        first_res.data_date = date.today() + relativedelta(days=1) - relativedelta(days=7)
        first_res.type = "file"
        first_res.save()
        send_dataset_update_reminder()
        assert len(mail.outbox) == 1
        assert mail.outbox[0].subject == "Test wysyłki notyfikacji dot. aktualizacji zbioru"
        assert mail.outbox[0].to == ["test-recipient@test.com"]
        assert mail.outbox[0].to != [admin.email]


class TestMetadataFileCreation:
    """
    Tests metadata file creation functionalities.

    Contains test methods for validating the creation of various types of metadata files
    and their proper handling under different conditions.

    The class includes tests for:
    - Creating XML and CSV metadata files.
    - Validating metadata file creation with previous file deletion.
    """

    @pytest.mark.parametrize(
        "extension, task",
        [
            ("xml", create_xml_metadata_files),
            ("csv", create_csv_metadata_files),
        ],
    )
    @pytest.mark.usefixtures("tmp_path", "mocker")
    def test_create_metadata_files(self, tmp_path: str, mocker: "MockerFixture", extension, task):
        """
        Tests the creation of XML metadata files.

        Validates the creation of XML metadata files by executing a specified task and
        verifying the existence of a file in 'tmp_path' with a specific naming format.

        Args:
        - tmp_path (str): Temporary directory provided for testing.
        - mocker (MockerFixture): Pytest mocker fixture for mocking objects.
        - extension (str): Expected extension of the metadata file.
        - task (callable): The task generating the metadata file.
        """
        with override_settings(METADATA_MEDIA_ROOT=tmp_path):
            # Create a mock for datetime.
            # Ensure that test will not fail due to datetime.today().date()
            new_today = self.mock_date(year=2023, month=12, day=24, mocker=mocker)

            task()
            file = Path(f"{tmp_path}") / f"pl/katalog_{new_today}.{extension}"
            assert file.is_file()

    @staticmethod
    def mock_date(mocker: "MockerFixture", year: int, month: int, day: int) -> date:
        """
        Mocks the current date with a specified year, month, and day.
        Returns:
        - new_today (datetime.date): The newly created date object with specified values.
        """
        new_today = date(year=year, month=month, day=day)
        datetime_mock = mocker.Mock()
        datetime_mock.today.return_value.date.return_value = new_today
        mocker.patch("mcod.datasets.tasks.datetime", datetime_mock)

        return new_today

    @pytest.mark.parametrize(
        "extension, task",
        [
            ("xml", create_xml_metadata_files),
            ("csv", create_csv_metadata_files),
        ],
    )
    @pytest.mark.usefixtures("tmp_path", "mocker")
    def test_create_metadata_files_with_deletion_previous(self, tmp_path, mocker, task, extension):
        """
        Tests metadata file creation with previous file deletion.

        Validates the creation of metadata files while simulating file deletion
        and recreation. It ensures the proper creation and deletion of files
        based on the specified conditions.
        """
        with override_settings(METADATA_MEDIA_ROOT=tmp_path):
            new_today = self.mock_date(year=2023, month=12, day=24, mocker=mocker)
            task()
            file = Path(f"{tmp_path}") / f"pl/katalog_{new_today}.{extension}"

            new_today2 = self.mock_date(year=2023, month=12, day=25, mocker=mocker)
            task()
            file2 = Path(f"{tmp_path}") / f"pl/katalog_{new_today2}.{extension}"

            assert not file.is_file()
            assert file2.is_file()

    def test_columns_in_csv_metadata_report(self, tmp_path: str, mocker: "MockerFixture"):
        """Check if required columns are present in csv metadata report."""

        columns_required = [
            "URL zbioru",
            "Tytuł",
            "Opis",
            "Słowo kluczowe",
            "Kategoria",
            "Częstotliwość aktualizacji",
            "Data udostępnienia zbioru",
            "Data aktualizacji zbioru",
            "Liczba wyświetleń zbioru",
            "Liczba pobrań zbioru",
            "Liczba danych",
            "Warunki wykorzystywania",
            "Licencja",
            "źródło",
            "Zbiór zawiera dane o wysokiej wartości",
            "Zbiór zawiera dane o wysokiej wartości z wykazu KE",
            "Zbiór zawiera dane dynamiczne",
            "Zbiór zawiera dane badawcze",
            "Lokalizacje zbiorów danych",
            "Dokumenty uzupełniające zbioru (nazwa, język, url, rozmiar pliku)",
            "URL dostawcy",
            "Rodzaj instytucji",
            "Nazwa",
            "Skrót",
            "Id Instytucji",
            "REGON",
            "EPUAP",
            "Adres do doręczeń elektronicznych",
            "Strona internetowa",
            "Data utworzenia dostawcy",
            "Data aktualizacji dostawcy",
            "Liczba zbiorów danych",
            "Liczba zasobów dostawcy",
            "Kod pocztowy",
            "Miasto",
            "Rodzaj ulicy",
            "Ulica",
            "Numer ulicy",
            "Numer mieszkania",
            "Email",
            "Telefon",
            "URL danych",
            "Tytuł danych",
            "Opis danych",
            "Data udostępnienia danych",
            "Dane na dzień",
            "Poziom otwartości danych",
            "Typ",
            "Format pliku",
            "Rozmiar pliku",
            "Liczba wyświetleń danych",
            "Liczba pobrań danych",
            "Tabela",
            "Mapa",
            "Wykres",
            "Zasób zawiera dane o wysokiej wartości",
            "Zasób zawiera dane o wysokiej wartości z wykazu KE",
            "Zasób zawiera dane dynamiczne",
            "Zasób zawiera dane badawcze",
            "Zawiera wykaz chronionych danych",
            "Lokalizacje danych",
            "URL pliku (do pobrania)",
            "znaki umowne",
            "Dokumenty uzupełniające zasobu (nazwa, język, url, rozmiar pliku)",
        ]

        with override_settings(METADATA_MEDIA_ROOT=tmp_path):
            new_today = self.mock_date(year=2023, month=10, day=10, mocker=mocker)
            create_csv_metadata_files()
            file = Path(tmp_path) / "pl" / f"katalog_{new_today}.csv"
            dataframe_report = pd.read_csv(file, sep=";")
            actual_columns = set(dataframe_report.columns)
            for column in columns_required:
                assert column in dataframe_report, f"{column} not found in {actual_columns}"
