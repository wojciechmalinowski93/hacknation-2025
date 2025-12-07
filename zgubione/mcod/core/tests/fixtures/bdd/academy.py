from dateutil.relativedelta import relativedelta
from django.utils import timezone
from pytest_bdd import given, parsers

from mcod.academy.factories import CourseFactory, CourseModuleFactory


@given(parsers.parse("finished course with id {course_id:d}"))
def finished_course_with_id(course_id):
    _course = CourseFactory.create(id=course_id, title="Finished course with id {}".format(course_id))
    data = {
        "course": _course,
        "start": timezone.now().date() - relativedelta(days=3),
    }
    CourseModuleFactory.create(**data)
    _course.save()
    return _course


@given(parsers.parse("planned course with id {course_id:d}"))
def planned_course_with_id(course_id):
    _course = CourseFactory.create(id=course_id, title="Planned course with id {}".format(course_id))
    data = {
        "course": _course,
        "start": timezone.now().date() + relativedelta(days=3),
    }
    CourseModuleFactory.create(**data)
    _course.save()
    return _course


@given(parsers.parse("current course with id {course_id:d}"))
def current_course_with_id(course_id):
    _course = CourseFactory.create(id=course_id, title="Current course with id {}".format(course_id))
    data = {
        "course": _course,
        "start": timezone.now().date(),
    }
    CourseModuleFactory.create(**data)
    _course.save()
    return _course


@given(parsers.parse("{planned:d} planned academy courses"))
def planned_courses(planned: int):
    return CourseModuleFactory.create_batch(size=planned, start=timezone.now().date() + relativedelta(days=3))


@given(parsers.parse("{current:d} current academy courses"))
def current_courses(current: int):
    return CourseModuleFactory.create_batch(size=current, start=timezone.now().date())


@given(parsers.parse("{finished:d} finished academy courses"))
def finished_courses(finished: int):
    return CourseModuleFactory.create_batch(size=finished, start=timezone.now().date() - relativedelta(days=3))
