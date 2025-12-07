import random
from typing import Dict, List, Tuple, Union
from unittest.mock import MagicMock, patch

import pytest

from mcod.resources.management.commands.calculate_openness_score import (
    Command,
    ErrorRecord,
    OpennessScoreRecalculationResults,
    RecalculatedResourceRecord,
)
from mcod.resources.score_computation import OpennessScoreValue


class DummyQuerySet:
    def __init__(self, items):
        self._items = items

    def iterator(self):
        return iter(self._items)

    def count(self):
        return len(self._items)


ResourceWithExpectedResult = Tuple[MagicMock, Union[RecalculatedResourceRecord, ErrorRecord]]


def create_resource_mock(
    pk: int,
    original_score: OpennessScoreValue,
    new_score: OpennessScoreValue,
    score_fail: bool = False,
) -> ResourceWithExpectedResult:
    """
    Helper function to create resource mock for openness score calculation.
    Returns mock of the resource and corresponding calculation result record.
    """
    resource = MagicMock()
    resource.pk = pk
    resource.openness_score = original_score
    if score_fail:
        exc_msg = f"Cannot calculate openness score for resource: {pk}"
        resource.get_openness_score.side_effect = Exception(exc_msg)
        return resource, (pk, exc_msg)
    else:
        resource.get_openness_score.return_value = (new_score, None)
        return resource, (pk, original_score, new_score)


def create_resources_mocks(
    res_up_to_date_count: int = 0,
    res_to_update_count: int = 0,
    errors_count: int = 0,
) -> Tuple[List[ResourceWithExpectedResult], List[ResourceWithExpectedResult], List[ResourceWithExpectedResult]]:
    res_ok: List[ResourceWithExpectedResult] = []
    res_to_update: List[ResourceWithExpectedResult] = []
    res_err: List[ResourceWithExpectedResult] = []

    possible_scores = (0, 1, 2, 3, 4, 5)
    pk = 0

    # Create up-to-date resources
    for i in range(res_up_to_date_count):
        score = random.choice(possible_scores)
        resource, record = create_resource_mock(
            pk=pk,
            original_score=score,
            new_score=score,  # same score value
            score_fail=False,
        )
        res_ok.append((resource, record))
        pk += 1

    # Create resources which needs update
    for i in range(res_to_update_count):
        original_score, new_score = random.sample(possible_scores, 2)
        resource, record = create_resource_mock(
            pk=pk,
            original_score=original_score,
            new_score=new_score,
            score_fail=False,
        )
        res_to_update.append((resource, record))
        pk += 1

    # Create resources with errors while openness score calculation
    for i in range(errors_count):
        score = random.choice(possible_scores)
        resource, record = create_resource_mock(
            pk=pk,
            original_score=score,
            new_score=score,  # value is insignificant
            score_fail=True,
        )
        res_err.append((resource, record))
        pk += 1

    return res_ok, res_to_update, res_err


@pytest.fixture
def command_instance() -> Command:
    cmd = Command()
    return cmd


@pytest.fixture
def mock_df_to_csv() -> MagicMock:
    with patch("pandas.DataFrame.to_csv") as mock_df_csv:
        yield mock_df_csv


@pytest.fixture
def mock_resource() -> MagicMock:
    with patch("mcod.resources.management.commands.calculate_openness_score.Resource") as mock_resource:
        yield mock_resource


CommandOptions = Dict[str, Union[str, int, bool, None]]


@pytest.fixture
def sample_options() -> CommandOptions:
    return {
        "pks": "",
        "first_pk": None,
        "last_pk": None,
        "update": False,
        "report_dir": ".",
    }


@pytest.mark.parametrize(
    "res_up_to_date, res_to_update, errors, update",
    [
        # dry-run mode
        (True, True, True, False),
        (True, False, False, False),
        (False, True, False, False),
        (False, False, True, False),
        (True, True, False, False),
        (True, False, True, False),
        (False, True, True, False),
        (False, False, False, False),
        # # update mode
        (True, True, True, True),
        (True, False, False, True),
        (False, True, False, True),
        (False, False, True, True),
        (True, True, False, True),
        (True, False, True, True),
        (False, True, True, True),
        (False, False, False, True),
    ],
)
def test_command_flow(
    res_up_to_date: bool,
    res_to_update: bool,
    errors: bool,
    update: bool,
    command_instance: Command,
    sample_options: CommandOptions,
):
    # GIVEN
    # Step 0: Arguments validation mocks
    mock_validate_command_args = MagicMock()
    command_instance._validate_command_arguments = mock_validate_command_args
    # Step 1: Openness score calculation mocks
    resources_up_to_date = MagicMock() if res_up_to_date else None
    resources_to_update = MagicMock() if res_to_update else None
    errors = MagicMock() if errors else None
    results = OpennessScoreRecalculationResults(
        resources_up_to_date=resources_up_to_date,
        resources_to_update=resources_to_update,
        errors=errors,
    )
    mock_recalculate_score = MagicMock()
    mock_recalculate_score.return_value = results
    command_instance._recalculate_openness_score = mock_recalculate_score
    # Step 2, 3: Reports creation mocks
    mock_create_success_report, mock_create_error_report = MagicMock(), MagicMock()
    command_instance._create_success_csv_report = mock_create_success_report
    command_instance._create_error_csv_report = mock_create_error_report
    # Step 4: Update DB mock
    mock_update_resource = MagicMock()
    command_instance._update_resources_openness_score = mock_update_resource
    command_instance.stdout = MagicMock()

    # WHEN
    # The calculate_openness_score command is called
    sample_options.update({"update": update})
    command_instance.handle(**sample_options)

    # THEN
    # Command arguments should always be validated
    assert mock_validate_command_args.call_count == 1
    # Resource score recalculation should always be made
    mock_recalculate_score.assert_called_once_with(**sample_options)

    if not any([resources_up_to_date, resources_to_update, errors]):
        # No further steps should be done if no resource recalculated
        assert mock_create_success_report.call_count == 0
        assert mock_create_error_report.call_count == 0
        assert mock_update_resource.call_count == 0

    else:
        # Success report should be created
        mock_create_success_report.assert_called_once_with(
            res_to_update=resources_to_update,
            res_up_to_date=resources_up_to_date,
            **sample_options,
        )
        # Error report should be created only if any error occurred
        (
            mock_create_error_report.assert_called_once_with(
                errors,
                **sample_options,
            )
            if errors
            else mock_create_error_report.assert_not_called()
        )
        # DB update should be made only for update mode (not dry-run)
        mock_update_resource.assert_called_once_with(resources_to_update) if update else mock_update_resource.assert_not_called()


class TestCommandGetResources:

    def test_get_resources_using_pks(
        self,
        mock_resource: MagicMock,
        command_instance: Command,
    ):
        dummy_qs = MagicMock()
        dummy_qs.filter.return_value = dummy_qs
        mock_resource.objects.only.return_value = dummy_qs

        options = {
            "pks": "1,3,5",
            "first_pk": None,
            "last_pk": None,
            "report_dir": ".",
        }

        qs = command_instance._get_resources_to_recalculate_qs(**options)

        dummy_qs.filter.assert_called_once_with(pk__in=["1", "3", "5"])
        assert qs == dummy_qs

    def test_get_resources_using_range_both(
        self,
        mock_resource: MagicMock,
        command_instance: Command,
    ):
        dummy_qs = MagicMock()
        dummy_qs.filter.return_value = dummy_qs
        mock_resource.objects.only.return_value = dummy_qs

        options = {
            "pks": "",
            "first_pk": 10,
            "last_pk": 20,
            "report_dir": ".",
        }
        qs = command_instance._get_resources_to_recalculate_qs(**options)

        dummy_qs.filter.assert_any_call(pk__gte=10)
        dummy_qs.filter.assert_any_call(pk__lte=20)

        assert dummy_qs.filter.call_count == 2
        assert qs == dummy_qs

    def test_get_resources_using_first_pk_only(
        self,
        mock_resource: MagicMock,
        command_instance: Command,
    ):
        dummy_qs = MagicMock()
        dummy_qs.filter.return_value = dummy_qs
        mock_resource.objects.only.return_value = dummy_qs

        options = {
            "pks": "",
            "first_pk": 15,
            "last_pk": None,
            "report_dir": ".",
        }

        qs = command_instance._get_resources_to_recalculate_qs(**options)

        dummy_qs.filter.assert_called_once_with(pk__gte=15)
        assert qs == dummy_qs

    def test_get_resources_using_last_pk_only(
        self,
        mock_resource: MagicMock,
        command_instance: Command,
    ):
        dummy_qs = MagicMock()
        dummy_qs.filter.return_value = dummy_qs
        mock_resource.objects.only.return_value = dummy_qs

        options = {
            "pks": "",
            "first_pk": None,
            "last_pk": 25,
            "report_dir": ".",
        }

        qs = command_instance._get_resources_to_recalculate_qs(**options)

        dummy_qs.filter.assert_called_once_with(pk__lte=25)
        assert qs == dummy_qs


@pytest.mark.parametrize(
    "res_up_to_date_count, res_to_update_count, errors_count",
    [
        (3, 2, 1),
        (1, 0, 0),
        (0, 2, 0),
        (0, 0, 3),
        (1, 2, 0),
        (1, 0, 3),
        (0, 2, 3),
        (0, 0, 0),
    ],
)
def test__recalculate_openness_score(
    res_up_to_date_count: int,
    res_to_update_count: int,
    errors_count: int,
    command_instance: Command,
    sample_options: CommandOptions,
):
    # GIVEN
    up_to_date, to_update, err = create_resources_mocks(
        res_up_to_date_count=res_up_to_date_count,
        res_to_update_count=res_to_update_count,
        errors_count=errors_count,
    )
    # Get only mocked resource objects
    res_up_to_date = [res for res, _ in up_to_date]
    res_to_update = [res for res, _ in to_update]
    res_err = [res for res, _ in err]
    # Prepare resources QuerySet
    dummy_qs = DummyQuerySet(res_to_update + res_up_to_date + res_err)
    mock_get_qs = MagicMock(return_value=dummy_qs)
    command_instance._get_resources_to_recalculate_qs = mock_get_qs
    # Prepare expected results
    exp_up_to_date = [exp_res for _, exp_res in up_to_date]
    exp_to_update = [exp_res for _, exp_res in to_update]
    exp_err = [exp_res for _, exp_res in err]

    # WHEN
    results: OpennessScoreRecalculationResults = command_instance._recalculate_openness_score(**sample_options)

    # THEN
    mock_get_qs.assert_called_once_with(**sample_options)
    assert results.resources_up_to_date == exp_up_to_date
    assert results.resources_to_update == exp_to_update
    assert results.errors == exp_err


@pytest.mark.parametrize("resources_to_update, chunks", [(0, 0), (5, 1), (1001, 2)])
def test_update_resource_openness_score(
    resources_to_update: int,
    chunks: int,
    command_instance: Command,
    mock_resource: MagicMock,
):
    # GIVEN
    mock_bulk_update = MagicMock()
    mock_resource.objects.bulk_update = mock_bulk_update

    mock_update_es_and_rdf_db = MagicMock()
    command_instance._update_es_and_rdf_db_for_resources = mock_update_es_and_rdf_db
    # Create resources to update
    _, to_update, _ = create_resources_mocks(0, resources_to_update, 0)
    res_to_update_records = [record for _, record in to_update]

    # WHEN
    command_instance._update_resources_openness_score(res_to_update_records)

    # THEN
    assert mock_bulk_update.call_count == chunks
    mock_update_es_and_rdf_db.assert_called_once() if resources_to_update else mock_update_es_and_rdf_db.assert_not_called()
