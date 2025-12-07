from typing import Iterable, List

import pytest

from mcod.celeryapp import app


def celery_beat_tasks() -> List[str]:
    result = []
    for schedule_name, task_def in app.conf.beat_schedule.items():
        task_name = task_def["task"]
        result.append(task_name)
    return result


@pytest.mark.parametrize("celery_beat_task", celery_beat_tasks())
def test_celery_configuration(celery_beat_task: str):
    # given
    app.autodiscover_tasks(force=True)
    # force=True is required, because the production version is lazy, thus missing some tasks,
    # e.g. mcod.searchhistories.tasks.save_searchhistories_task
    registered_tasks: Iterable[str] = app.tasks.keys()
    # then
    assert celery_beat_task in registered_tasks, f"{celery_beat_task} not found in by celery"
