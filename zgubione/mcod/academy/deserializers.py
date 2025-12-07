from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from elasticsearch_dsl import Q
from marshmallow import validate

from mcod.core.api.schemas import ListingSchema, ListTermsSchema, NumberTermSchema
from mcod.core.api.search import fields as search_fields

COURSE_STATE_CHOICES = ["current", "finished", "planned"]


class CourseStateField(search_fields.ListTermsField):
    def q(self, value):
        today = timezone.now().date()
        states = list(set(value))
        should = []
        for state in states:
            if state == "planned":
                should.append(Q("range", **{"start": {"gt": today}}))
            elif state == "finished":
                should.append(Q("range", **{"end": {"lt": today}}))
            elif state == "current":
                should.append(Q("range", **{"start": {"lte": today}}) & Q("range", **{"end": {"gte": today}}))

        return Q("bool", should=should, minimum_should_match=1)


class CourseStateTermsSchema(ListTermsSchema):
    terms = CourseStateField(
        example="current,finished,planned",
        validate=validate.ContainsOnly(
            choices=COURSE_STATE_CHOICES,
            error=_("Invalid choice! Valid are: %(choices)s.") % {"choices": COURSE_STATE_CHOICES},
        ),
    )

    class Meta:
        default_field = "terms"


class CourseApiSearchRequest(ListingSchema):
    id = search_fields.FilterField(
        NumberTermSchema,
        doc_template="docs/generic/fields/number_term_field.html",
        doc_base_url="/courses",
        doc_field_name="ID",
    )
    state = search_fields.FilterField(
        CourseStateTermsSchema,
        doc_template="docs/generic/fields/string_term_field.html",
        doc_base_url="/courses",
        doc_field_name="state",
    )
    sort = search_fields.SortField(
        sort_fields={
            "id": "id",
            "start": "start",
            "participants_number": "participants_number",
        },
        doc_base_url="/courses",
    )

    class Meta:
        strict = True
        ordered = True
