import marshmallow as ma
from django.utils.translation import get_language


class Tags(ma.fields.List):
    def _serialize(self, value, attr, obj, **kwargs):
        lang = get_language()
        names = [tag.name for tag in value.filter(language=lang)]
        return [name for name in names if name is not None]
