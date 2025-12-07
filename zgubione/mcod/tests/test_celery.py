import pytest
from django.test import override_settings

from mcod.celeryapp import app as celery_app, get_beat_schedule
from mcod.settings.base import CELERY_TASK_DEFAULT_QUEUE, CELERY_TASK_ROUTES


def test_all_beat_tasks_have_queue_defined():
    """Check if all tasks running by Celery Beat (also monthly tasks)
    have defined queue other than the `default`.
    """
    celery_app.conf.beat_schedule = get_beat_schedule(enable_monthly_reports=True, enable_create_xml_metadata_report=True)
    missing_or_default_tasks = []

    for name, task in celery_app.conf.beat_schedule.items():
        queue = task.get("options", {}).get("queue")
        if not queue or queue == "default":
            missing_or_default_tasks.append(name)

    assert not missing_or_default_tasks


@override_settings(
    CELERY_TASK_DEFAULT_QUEUE=CELERY_TASK_DEFAULT_QUEUE,
    CELERY_TASK_ROUTES=CELERY_TASK_ROUTES,
)
def test_all_nonbeat_tasks_have_queue_defined():
    """Check if all tasks not runnning by Celery Beat,
    have defined queue other than the `default`.
    """
    router = celery_app.amqp.router
    missing_or_default_tasks = []

    beat_task_names = {
        val["task"] for val in get_beat_schedule(enable_monthly_reports=True, enable_create_xml_metadata_report=True).values()
    }

    for name in celery_app.tasks:
        if name.startswith("celery."):
            continue  # internal celery tasks
        if name.startswith("test_") or ".tests." in name:
            continue  # celery test tasks
        if name in beat_task_names:
            continue  # celery beat tasks

        route = router.route({}, name)
        queue = route.get("queue", "default")
        queue_name = queue.name if hasattr(queue, "name") else queue
        if queue_name == "default":
            missing_or_default_tasks.append(name)

    assert not missing_or_default_tasks


@pytest.mark.parametrize(
    ["data_to_change_beat_schedule", "crontab_before_change", "crontab_after_change"],
    [
        pytest.param(
            '{"kronika_sparql_performance": {"day_of_month":5, "hour": 10, "minute": 20}}',
            "<crontab: 30 11 * * * (m/h/dM/MY/d)>",
            "<crontab: 20 10 5 * * (m/h/dM/MY/d)>",
            id="task start time changed correctly",
        ),
        pytest.param(
            '{"kronika_sparql_performance": {"day_of_month":5, "hour": 10, "minute": 20},'
            ' "catalog_xml_file_creation":{"hour": 7, "minute": 5}}',
            "<crontab: 30 11 * * * (m/h/dM/MY/d)>",
            "<crontab: 20 10 5 * * (m/h/dM/MY/d)>",
            id="task start time changed correctly when also other task will be changed and data are correct",
        ),
        pytest.param(
            '{"kronika_sparql_performance": {"day_of_month":5, "hour": 10000, "minute": 20}}',
            "<crontab: 30 11 * * * (m/h/dM/MY/d)>",
            "<crontab: 30 11 * * * (m/h/dM/MY/d)>",
            id="task start time not changed - data for task are incorrect",
        ),
        pytest.param(
            '{"kronika_sparql_performance": {"day_of_month":5, "hour": 10, "minute": 20},'
            ' "catalog_xml_file_creation":{"hour": 200, "minute": 5}}',
            "<crontab: 30 11 * * * (m/h/dM/MY/d)>",
            "<crontab: 30 11 * * * (m/h/dM/MY/d)>",
            id="task start time not changed - data for other task are incorrect",
        ),
    ],
)
def test_change_period_task_start_time(data_to_change_beat_schedule: str, crontab_before_change: str, crontab_after_change: str):
    original_schedule: dict = get_beat_schedule(enable_monthly_reports=False, enable_create_xml_metadata_report=True)
    changed_beat_schedule: dict = get_beat_schedule(
        enable_monthly_reports=False,
        enable_create_xml_metadata_report=True,
        update_beat_schedule_data=data_to_change_beat_schedule,
    )

    assert str(original_schedule["kronika_sparql_performance"]["schedule"]) == crontab_before_change
    assert str(changed_beat_schedule["kronika_sparql_performance"]["schedule"]) == crontab_after_change


@pytest.mark.parametrize("enable_create_xml_metadata_report_value", [True, False])
def test_catalog_xml_file_creation_task_in_beat_schedule_depends_on_enable_create_xml_metadata_report_parameter(
    enable_create_xml_metadata_report_value: bool,
):

    beat_schedule: dict = get_beat_schedule(
        enable_monthly_reports=False,
        enable_create_xml_metadata_report=enable_create_xml_metadata_report_value,
    )

    assert enable_create_xml_metadata_report_value == ("catalog_xml_file_creation" in beat_schedule)
