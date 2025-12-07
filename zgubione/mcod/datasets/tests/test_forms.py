from typing import Any, Dict, Optional, Set, Tuple

import pytest
from django.utils.translation import gettext_lazy as _

from mcod.datasets.forms import UPDATE_FREQUENCY_FOR_CREATE, DatasetForm
from mcod.datasets.models import UPDATE_FREQUENCY, Dataset
from mcod.resources.factories import DatasetFactory
from mcod.tags.models import Tag


def test_not_present_values_in_create_dataset_form():
    values_forbidden_for_create: Set[Tuple[Optional[str], str]] = set(UPDATE_FREQUENCY) - set(UPDATE_FREQUENCY_FOR_CREATE)
    assert values_forbidden_for_create == {("notApplicable", _("Not applicable"))}


@pytest.mark.parametrize(
    ("action", "update_frequency_value", "form_shoud_be_valid", "error_info"),
    [
        # create Dataset
        ("create", "", False, "To pole jest obowiązkowe."),
        ("create", "daily", True, ""),
        ("create", "weekly", True, ""),
        ("create", "monthly", True, ""),
        ("create", "quarterly", True, ""),
        ("create", "everyHalfYear", True, ""),
        ("create", "yearly", True, ""),
        ("create", "irregular", True, ""),
        ("create", "notPlanned", True, ""),
        ("create", "notApplicable", False, "Wybierz poprawną wartość. notApplicable nie jest żadną z dostępnych opcji."),
        # update Dataset
        ("update", "", False, "To pole jest obowiązkowe."),
        ("update", "daily", True, ""),
        ("update", "weekly", True, ""),
        ("update", "monthly", True, ""),
        ("update", "quarterly", True, ""),
        ("update", "everyHalfYear", True, ""),
        ("update", "yearly", True, ""),
        ("update", "irregular", True, ""),
        ("update", "notPlanned", True, ""),
        ("update", "notApplicable", False, "Wartość 'Nie dotyczy' nie jest już obsługiwana przez portal. Zmień ją na inną."),
    ],
)
def test_dataset_form_update_frequency_field_for_create_and_update_dataset(
    post_data_to_create_dataset: Dict[str, Any],
    tag_pl: Tag,
    action: str,
    update_frequency_value: str,
    form_shoud_be_valid: bool,
    error_info: str,
):
    dataset_db: Dataset = DatasetFactory.create(update_frequency="daily")

    post_data = post_data_to_create_dataset
    post_data["title"] = "Some dataset to create"
    post_data["update_frequency"] = update_frequency_value
    post_data["organization"] = dataset_db.organization.id
    post_data["categories"] = [dataset_db.category.id]
    post_data["tags"] = [tag_pl.id]
    post_data["tags_pl"] = [tag_pl.id]

    if action == "create":
        form = DatasetForm(data=post_data)
    else:  # update action
        form = DatasetForm(data=post_data, instance=dataset_db)

    validation_result: bool = form.is_valid()

    if form_shoud_be_valid:
        assert validation_result
    else:
        assert not validation_result
        assert form.errors["update_frequency"][0] == error_info
