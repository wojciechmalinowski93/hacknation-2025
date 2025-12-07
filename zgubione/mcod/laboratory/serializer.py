from mcod.core.api import fields
from mcod.core.api.jsonapi.serializers import ObjectAttrs, TopLevel
from mcod.lib.serializers import TranslatedStr


class ReportSchema(ObjectAttrs):
    type = fields.Str()
    download_url = fields.Str()
    link = fields.Str()

    class Meta:
        ordered = True


class LaboratoryApiAttrs(ObjectAttrs):
    title = TranslatedStr()
    notes = TranslatedStr()
    event_type = fields.String()
    execution_date = fields.Date()
    reports = fields.Nested(ReportSchema, many=True)

    class Meta:
        object_type = "Laboratory"
        url_template = "{api_url}/laboratories/{ident}"
        model = "laboratory.LabEvent"


class LaboratoriesApiResponse(TopLevel):
    class Meta:
        attrs_schema = LaboratoryApiAttrs
