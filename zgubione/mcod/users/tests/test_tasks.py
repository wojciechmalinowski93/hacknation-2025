from pathlib import Path

import pandas as pd
from django.test import override_settings

from mcod.reports.tasks import generate_csv
from mcod.users.models import User


class TestUserCSV:

    def test_columns_in_user_csv_report(self, tmp_path: str, active_user):
        """Check if required columns are present in csv metadata report."""

        columns_required = [
            "id",
            "Email",
            "Imię i nazwisko",
            "telefon służbowy",
            "Edytor",
            "Urzędnik",
            "Administrator",
            "Administrator AOD",
            "Administrator LOD",
            "Pełnomocnik",
            "Dodatkowy pełnomocnik",
            "Stan",
            "Instytucja1",
            "Instytucja2",
            "Powiązanie z WK",
            "Sposób ostatniego logowania",
            "Data ostatniego logowania",
        ]

        with override_settings(REPORTS_MEDIA_ROOT=tmp_path):
            file_name_postfix = "csv_test"
            user_ids = [user.pk for user in User.objects.all()]
            generate_csv(user_ids, "users.User", active_user.pk, file_name_postfix)
            filename = "users_" + file_name_postfix + ".csv"
            file = Path(tmp_path) / "users" / filename
            dataframe_report = pd.read_csv(file, sep=";")

            for column in columns_required:
                assert column in dataframe_report
