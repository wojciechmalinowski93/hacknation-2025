from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from taggit.models import Tag

from mcod.core.tasks import SharedTask, extended_shared_task
from mcod.core.tests.helpers.tasks import run_on_commit_events


def with_side_effect(
    tag_name: str,
    raise_after: Exception | None = None,
) -> None:
    Tag.objects.create(name=tag_name)
    if raise_after:
        raise raise_after


@pytest.mark.celery
class TestRetry:
    @pytest.fixture
    def unreliable_resource(self):
        return MagicMock(
            side_effect=(
                ZeroDivisionError("1/3"),
                ZeroDivisionError("2/3"),
                ZeroDivisionError("3/3"),
                None,
            )
        )

    def test_retry_with_celery(self, unreliable_resource):
        # Given
        @extended_shared_task(
            max_retries=10,
            retry_on_errors=(ZeroDivisionError,),
            retry_countdown=100,  # ignored in eager mode,
            name="test_retry_with_celery",  # required, otherwise the task name will clash
        )
        def resource_using_fn(tag_name: str) -> None:
            unreliable_resource()
            Tag.objects.create(name=tag_name)

        tag_name = str(uuid4())
        assert not Tag.objects.filter(name=tag_name).exists()
        # When
        resource_using_fn.s(tag_name).apply_async()
        # Then
        assert Tag.objects.filter(name=tag_name).exists()
        assert unreliable_resource.call_count == 4, "Function should retry until unreliable_resource doesn't raise."

    def test_celery_obeys_max_retries(self, unreliable_resource):
        # Given
        max_retries = 2

        @extended_shared_task(
            max_retries=max_retries,
            retry_on_errors=(ZeroDivisionError,),
            retry_countdown=100,  # ignored in eager mode,
            name="test_celery_obeys_max_retries",
        )
        def resource_using_fn(tag_name: str) -> None:
            unreliable_resource()
            Tag.objects.create(name=tag_name)

        tag_name = str(uuid4())
        # When
        resource_using_fn.s(tag_name).apply_async()
        # Then
        assert not Tag.objects.filter(name=tag_name).exists()
        assert unreliable_resource.call_count == max_retries + 1, f"Function should run once plus {max_retries} retries"

    def test_retry_using_lambda(self, unreliable_resource):
        max_retries = 3

        # Given
        @extended_shared_task(
            max_retries=max_retries,
            retry_on_lambda=lambda exc: exc.args
            in (
                ("1/3",),
                ("unmatched",),
            ),
            retry_countdown=100,  # ignored in eager mode,
            name="test_retry_using_lambda",
        )
        def resource_using_fn() -> None:
            unreliable_resource()

        # When
        resource_using_fn.apply_async()
        # Then
        assert unreliable_resource.call_count == 1 + 1, "Retries should stop after first unmatched error"

    def test_retry_using_lambda_and_exception_list(self):
        # Given
        unreliable_resource = MagicMock(
            side_effect=(
                KeyError("1/3"),
                ValueError("2/3"),
                ZeroDivisionError("3/3"),
                None,
            )
        )

        # Given
        @extended_shared_task(
            max_retries=3,
            retry_on_lambda=lambda exc: exc.args
            in (
                ("1/3",),
                ("2/3",),  # overlaps with retry_on_errors
            ),
            retry_on_errors=(ZeroDivisionError, ValueError),
            retry_countdown=100,  # ignored in eager mode,
            name="test_retry_using_lambda_and_exception_list",
        )
        def resource_using_fn_local(tag_name: str) -> None:
            unreliable_resource()
            Tag.objects.create(name=tag_name)

        tag_name = str(uuid4())
        assert not Tag.objects.filter(name=tag_name).exists()
        # When
        resource_using_fn_local.s(tag_name).apply_async()
        # Then
        assert Tag.objects.filter(name=tag_name).exists()
        assert unreliable_resource.call_count == 4, "Function should run until success, all 3 exceptions should match"


class TestAtomic:
    def test_atomic(self):
        # Given
        tag_name = str(uuid4())
        assert not Tag.objects.filter(name=tag_name).exists()
        decorated = extended_shared_task(
            atomic=True,
            name="test_atomic",
        )(with_side_effect)
        # When
        decorated(tag_name)
        # Then
        assert Tag.objects.filter(name=tag_name).exists()

    def test_atomic_commit_on_errors(self):
        # Given
        tag_name = str(uuid4())
        assert not Tag.objects.filter(name=tag_name).exists()
        decorated = extended_shared_task(
            atomic=True,
            commit_on_errors=(TypeError,),
            name="test_atomic_commit_on_errors",
        )(with_side_effect)
        # When/Then
        with pytest.raises(TypeError):
            # When
            decorated(tag_name, raise_after=TypeError)
        assert Tag.objects.filter(name=tag_name).exists()

    def test_atomic_commit_on_errors_rollback(self):
        # Given
        tag_name = str(uuid4())
        assert not Tag.objects.filter(name=tag_name).exists()
        decorated = extended_shared_task(
            atomic=True,
            commit_on_errors=(ValueError,),
            name="test_atomic_commit_on_errors_rollback",
        )(with_side_effect)
        # When/Then
        with pytest.raises(TypeError):  # different error type than the one above
            # When
            decorated(tag_name, raise_after=TypeError)
        assert not Tag.objects.filter(name=tag_name).exists()


@pytest.mark.celery
class TestApplyAsync:
    def test_apply_async_on_commit(self):
        # Given
        @extended_shared_task(
            name="test_apply_async_on_commit",
            apply_async_on_commit=True,  # included for clarity
        )
        def resource_using_fn(tag_name: str) -> None:
            Tag.objects.create(name=tag_name)

        tag_name = str(uuid4())
        # When
        resource_using_fn.apply_async_on_commit(args=(tag_name,))
        # Then
        assert not Tag.objects.filter(name=tag_name).exists()
        # When
        run_on_commit_events()
        # Then
        assert Tag.objects.filter(name=tag_name).exists()

    def test_apply_async_on_commit_via_signature(self):
        # Given
        @extended_shared_task(
            name="test_apply_async_on_commit_via_signature",
            apply_async_on_commit=True,  # included for clarity
        )
        def resource_using_fn(tag_name: str) -> None:
            Tag.objects.create(name=tag_name)

        tag_name = str(uuid4())
        # When
        resource_using_fn.s(tag_name).apply_async_on_commit()
        # Then
        assert not Tag.objects.filter(name=tag_name).exists()
        # When
        run_on_commit_events()
        # Then
        assert Tag.objects.filter(name=tag_name).exists()


class TestDeveloperInterface:
    def test_argument_validation(self):
        with pytest.warns(
            UserWarning,
            match="implies atomic",
        ):
            SharedTask(commit_on_errors=(Exception,))._validate_args(with_side_effect)
        with pytest.warns(UserWarning, match="retry_on_errors has precedence over retry_on_lambda"):
            SharedTask(
                max_retries=1,
                retry_on_errors=(Exception,),
                retry_on_lambda=lambda x: True,
            )._validate_args(with_side_effect)
        with pytest.raises(ValueError, match="retry_on_lambda didn't return boolean when checked"):
            SharedTask(
                max_retries=1,
                retry_on_lambda=lambda x: 42,  # noqa
            )._validate_args(with_side_effect)

    def test_cant_redecorate(self):
        # Given
        decorated = extended_shared_task(with_side_effect, name="test_cant_redecorate")
        with pytest.raises(TypeError, match="re-decorate"):
            # When
            extended_shared_task(decorated)

    def test_str_works(self):
        assert str(SharedTask()) == (
            "SharedTask(apply_async_on_commit=True,"
            "atomic=False,commit_on_errors=(),"
            "retry_on_errors=(),"
            "retry_on_lambda=None,"
            "retry_countdown=300,"
            "bind=False,"
            "celery_kwargs={},)"
        )
        assert "retry_on_errors=(<class 'ZeroDivisionError'>,),retry_on_lambda=<lambda>," in str(
            SharedTask(
                retry_on_errors=(ZeroDivisionError,),
                retry_on_lambda=lambda x: False,
            )
        )
        assert "celery_kwargs={'ignore_results': True}" in (
            str(
                SharedTask(
                    retry_on_errors=(ZeroDivisionError,),
                    ignore_results=True,
                )
            )
        )

    def test_str_works_with_function(self):
        def named_exception_handler(e: Exception) -> bool:
            return False

        assert "retry_on_lambda=named_exception_handler" in str(SharedTask(retry_on_lambda=named_exception_handler))
