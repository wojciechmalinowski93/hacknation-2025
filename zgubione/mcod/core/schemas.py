from marshmallow import Schema

from mcod.lib import fields


class StatsSchema(Schema):
    explain = fields.Raw()

    class Meta:
        strict = True
