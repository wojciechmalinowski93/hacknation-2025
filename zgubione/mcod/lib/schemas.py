from django.utils.translation import gettext as _
from marshmallow import Schema, ValidationError, validates

from mcod.lib import fields


class ErrorSchema(Schema):
    title = fields.Str()
    description = fields.Str()
    code = fields.Str()
    errors = fields.Dict()
    traceback = fields.Str()


class List(Schema):
    page = fields.Integer(data_key="page", missing=1, example=5)
    per_page = fields.Integer(missing=20, example=20)
    explain = fields.Raw(missing=False)

    @validates("page")
    def validate_page(self, n):
        if n < 1:
            raise ValidationError(_("Page must be greater then 1"))

    @validates("per_page")
    def validate_per_page(self, n):
        if n < 1:
            raise ValidationError(_("Page size mus be greater then 0"))
        if n > 100:
            raise ValidationError(_("Max page size is 100"))

    class Meta:
        strict = True
