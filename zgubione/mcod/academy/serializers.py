from django.utils import timezone
from marshmallow import pre_dump

from mcod.academy.models import Course
from mcod.core.api import fields
from mcod.core.api.jsonapi.serializers import HighlightObjectMixin, ObjectAttrs, TopLevel
from mcod.watchers.serializers import SubscriptionMixin


class CourseModuleSchema(ObjectAttrs):
    id = fields.Int()
    type = fields.Str()
    type_name = fields.Str()
    start = fields.Date()
    end = fields.Date()

    class Meta:
        ordered = True


class CourseApiAttrs(ObjectAttrs, HighlightObjectMixin):
    title = fields.Str()
    notes = fields.Str()
    participants_number = fields.Int()
    venue = fields.Str()
    start = fields.Date()
    end = fields.Date()
    file_type = fields.Str()
    file_url = fields.URL()
    materials_file_type = fields.Str()
    materials_file_url = fields.URL()
    sessions = fields.Nested(CourseModuleSchema, many=True)
    state = fields.Str()
    state_name = fields.Str()

    class Meta:
        object_type = "course"
        url_template = "{api_url}/courses/{ident}"
        model = "academy.Course"

    @pre_dump
    def prepare_data(self, data, **kwargs):
        if data.start and data.end:
            today = timezone.now().date()
            start_date = data.start.date()
            end_date = data.end.date()
            _state = None
            if start_date <= today <= end_date:
                _state = "current"
            elif end_date < today:
                _state = "finished"
            elif today < start_date:
                _state = "planned"
            if _state:
                setattr(data, "state", _state)
                setattr(data, "state_name", Course.COURSE_STATES.get(_state))
        return data


class CourseApiResponse(SubscriptionMixin, TopLevel):
    class Meta:
        attrs_schema = CourseApiAttrs
