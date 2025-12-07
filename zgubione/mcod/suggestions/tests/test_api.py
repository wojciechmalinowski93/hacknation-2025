import pytest
from falcon import HTTP_201, HTTP_401, HTTP_CONFLICT, HTTP_NOT_FOUND, HTTP_OK, testing
from falcon.testing import Result
from pytest_bdd import scenarios

from mcod.core.tests.helpers.tasks import run_on_commit_events
from mcod.suggestions.models import AcceptedDatasetSubmission
from mcod.suggestions.tasks import deactivate_accepted_dataset_submissions, send_data_suggestion

scenarios(
    "features/api/accepteddatasetsubmission_list.feature",
    "features/api/submissions.feature",
)


@pytest.mark.elasticsearch
def test_only_published_accepted_submission_in_public_list_view(
    public_accepted_dataset_submission, accepted_dataset_submission, client14
):
    run_on_commit_events()
    resp = client14.simulate_get("/submissions/accepted/public")
    assert HTTP_OK == resp.status
    assert len(resp.json["data"]) == 1
    assert resp.json["data"][0]["attributes"]["title"] == "public test title"
    assert resp.json.get("jsonapi")


@pytest.mark.elasticsearch
def test_published_accepted_submission_in_public_details_view(public_accepted_dataset_submission, client14):
    obj_id = public_accepted_dataset_submission.pk
    resp = client14.simulate_get(f"/submissions/accepted/public/{obj_id}")
    assert HTTP_OK == resp.status
    assert resp.json["data"]["attributes"]["title"] == "public test title"
    assert resp.json.get("jsonapi")


@pytest.mark.elasticsearch
def test_unpublished_accepted_submission_not_in_public_details_view(accepted_dataset_submission, client14):
    obj_id = accepted_dataset_submission.pk
    resp = client14.simulate_get(f"/submissions/accepted/public/{obj_id}")
    assert HTTP_NOT_FOUND == resp.status


@pytest.mark.elasticsearch
def test_send_data_suggestion_task(suggestion):
    result = send_data_suggestion.delay(suggestion.id)
    assert result.result["suggestion"] == "test suggestion notes"


@pytest.mark.elasticsearch
def test_deactivate_accepted_dataset_submissions_task():
    result = deactivate_accepted_dataset_submissions.delay()
    assert result.result["deactivated"] == 0


@pytest.mark.parametrize("feedback", ["minus", "plus"])
def test_suggestion_feedback_success(
    client14_logged_admin: testing.TestClient, accepted_dataset_submission: AcceptedDatasetSubmission, feedback: str
):
    # GIVEN
    feedback_data = {"data": {"type": "feedback", "attributes": {"opinion": feedback}}}
    dataset_submission_id: int = accepted_dataset_submission.pk
    assert accepted_dataset_submission.feedback_counters == {"minus": 0, "plus": 0}
    # WHEN
    resp: Result = client14_logged_admin.simulate_post(
        f"/submissions/accepted/{dataset_submission_id}/feedback", json=feedback_data
    )
    # THEN
    assert resp.status == HTTP_201
    if feedback == "plus":
        assert accepted_dataset_submission.feedback_counters == {"minus": 0, "plus": 1}
    else:
        assert accepted_dataset_submission.feedback_counters == {"minus": 1, "plus": 0}


@pytest.mark.parametrize(
    "submission_status, response_status",
    [("draft", HTTP_CONFLICT), ("publication_finished", HTTP_CONFLICT), ("published", HTTP_201)],
)
def test_suggestion_status_vs_feedback_response_status(
    client14_logged_admin: testing.TestClient,
    accepted_dataset_submission: AcceptedDatasetSubmission,
    submission_status: str,
    response_status: str,
):
    # GIVEN
    feedback_data = {"data": {"type": "feedback", "attributes": {"opinion": "plus"}}}
    dataset_submission_id: int = accepted_dataset_submission.pk
    accepted_dataset_submission.status = submission_status
    accepted_dataset_submission.save()
    # WHEN
    resp: Result = client14_logged_admin.simulate_post(
        f"/submissions/accepted/{dataset_submission_id}/feedback", json=feedback_data
    )
    # THEN
    assert resp.status == response_status


def test_suggestion_deleted_feedback_response_status(
    client14_logged_admin: testing.TestClient, accepted_dataset_submission: AcceptedDatasetSubmission
):
    # GIVEN
    feedback_data = {"data": {"type": "feedback", "attributes": {"opinion": "plus"}}}
    dataset_submission_id: int = accepted_dataset_submission.pk
    accepted_dataset_submission.delete()
    # WHEN
    resp: Result = client14_logged_admin.simulate_post(
        f"/submissions/accepted/{dataset_submission_id}/feedback", json=feedback_data
    )
    # THEN
    assert resp.status == HTTP_NOT_FOUND


@pytest.mark.parametrize("is_active, response_status", [(True, HTTP_201), (False, HTTP_CONFLICT)])
def test_suggestion_active_inactive_feedback_response(
    client14_logged_admin: testing.TestClient,
    accepted_dataset_submission: AcceptedDatasetSubmission,
    is_active: bool,
    response_status: str,
):
    # GIVEN
    feedback_data = {"data": {"type": "feedback", "attributes": {"opinion": "plus"}}}
    dataset_submission_id: int = accepted_dataset_submission.pk
    accepted_dataset_submission.is_active = is_active
    accepted_dataset_submission.save()
    # WHEN
    resp: Result = client14_logged_admin.simulate_post(
        f"/submissions/accepted/{dataset_submission_id}/feedback", json=feedback_data
    )
    # THEN
    assert resp.status == response_status


def test_not_logged_client_can_not_feedback(client14: testing.TestClient, accepted_dataset_submission: AcceptedDatasetSubmission):
    # GIVEN
    feedback_data = {"data": {"type": "feedback", "attributes": {"opinion": "plus"}}}
    dataset_submission_id: int = accepted_dataset_submission.pk
    assert accepted_dataset_submission.feedback_counters == {"minus": 0, "plus": 0}
    # WHEN
    resp: Result = client14.simulate_post(f"/submissions/accepted/{dataset_submission_id}/feedback", json=feedback_data)
    # THEN
    assert resp.status == HTTP_401
    assert accepted_dataset_submission.feedback_counters == {"minus": 0, "plus": 0}
