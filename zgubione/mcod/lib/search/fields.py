from django_elasticsearch_dsl import fields

from mcod import settings
from mcod.core.api.search.analyzers import polish_analyzer, polish_asciied, standard_asciied
from mcod.core.api.search.fields import ICUSortField


class TranslatedTextField(fields.NestedField):
    asciied = {
        "pl": polish_asciied,
    }

    def __init__(
        self,
        field_name,
        *args,
        raw_field_cls=None,
        attr=None,
        analyzers=None,
        properties=None,
        **kwargs,
    ):
        raw_field_cls = raw_field_cls if raw_field_cls else fields.KeywordField
        if not properties:
            properties = {
                lang_code: fields.TextField(
                    fields={
                        "raw": raw_field_cls(),
                        "sort": ICUSortField(index=False, language=lang_code, country=lang_code.upper()),
                        "asciied": fields.TextField(analyzer=self.asciied.get(lang_code, standard_asciied)),
                    }
                )
                for lang_code in settings.MODELTRANS_AVAILABLE_LANGUAGES
            }

        if analyzers:
            for lang_code in settings.MODELTRANS_AVAILABLE_LANGUAGES:
                if lang_code in analyzers:
                    properties[lang_code].analyzer = analyzers[lang_code]
        else:
            properties["pl"].analyzer = polish_analyzer

        attr = attr or field_name
        super().__init__(*args, attr=f"{attr}_translated", properties=properties, **kwargs)


class TranslatedSuggestField(TranslatedTextField):
    def __init__(self, field_name, *args, attr=None, analyzers=None, properties=None, **kwargs):
        if not properties:
            properties = {
                lang_code: fields.TextField(
                    fields={
                        "raw": fields.KeywordField(),
                        "sort": ICUSortField(index=False, language=lang_code, country=lang_code.upper()),
                        "asciied": fields.TextField(analyzer=self.asciied.get(lang_code, standard_asciied)),
                        "suggest": fields.CompletionField(),
                    }
                )
                for lang_code in settings.MODELTRANS_AVAILABLE_LANGUAGES
            }

        super().__init__(
            field_name,
            *args,
            attr=attr,
            analyzers=analyzers,
            properties=properties,
            **kwargs,
        )


class TranslatedKeywordField(fields.NestedField):
    def __init__(
        self,
        field_name,
        *args,
        attr=None,
        field_kwargs=None,
        properties=None,
        multi=True,
        **kwargs,
    ):
        field_kwargs = field_kwargs or {}
        properties = properties or {
            lang_code: fields.KeywordField(**field_kwargs) for lang_code in settings.MODELTRANS_AVAILABLE_LANGUAGES
        }
        attr = attr or field_name

        super().__init__(
            *args,
            attr=f"{attr}_translated",
            properties=properties,
            multi=True,
            **kwargs,
        )
