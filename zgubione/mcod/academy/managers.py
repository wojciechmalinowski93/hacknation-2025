from django.db.models import Case, CharField, Count, Max, Min, Q, Value, When
from django.utils import timezone

from mcod.core.db.managers import TrashManager
from mcod.core.managers import SoftDeletableManager, SoftDeletableQuerySet, TrashQuerySet


class CourseQuerySetMixin:
    def published(self):
        return self.filter(status="published")

    def with_schedule(self):
        today = timezone.now().date()
        q_modules_not_removed = Q(modules__is_removed=False, modules__is_permanently_removed=False)
        return self.annotate(
            _start=Min("modules__start", filter=q_modules_not_removed),
            _end=Max("modules__end", filter=q_modules_not_removed),
            _modules_count=Count("modules", filter=q_modules_not_removed),
            _course_state=Case(
                When(_start__lte=today, _end__gte=today, then=Value("current")),
                When(_start__gt=today, then=Value("planned")),
                When(_end__lt=today, then=Value("finished")),
                default=Value(""),
                output_field=CharField(),
            ),
        )


class CourseQuerySet(CourseQuerySetMixin, SoftDeletableQuerySet):
    pass


class CourseTrashQuerySet(CourseQuerySetMixin, TrashQuerySet):
    pass


class CourseManager(SoftDeletableManager):
    _queryset_class = CourseQuerySet

    def published(self):
        return super().get_queryset().published()

    def with_schedule(self):
        return super().get_queryset().with_schedule()


class CourseTrashManager(TrashManager):
    _queryset_class = CourseTrashQuerySet

    def with_schedule(self):
        return super().get_queryset().with_schedule()
