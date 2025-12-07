import json
from typing import Any, Dict, List

import more_itertools as mit
from ckeditor.widgets import CKEditorWidget as BaseCKEditorWidget
from ckeditor_uploader.fields import RichTextUploadingField as BaseRichTextUploadingField
from ckeditor_uploader.widgets import CKEditorUploadingWidget as BaseCKEditorUploadingWidget
from django.conf import settings
from django.forms import CheckboxSelectMultiple, Widget, fields
from django.template.loader import get_template
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _


class CheckboxSelect(CheckboxSelectMultiple):
    allow_multiple_selected = False


class CKEditorMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config["language_list"] = ["pl:Polski", "en:Angielski"]
        toolbar_name = self.config.get("toolbar")
        if toolbar_name:
            toolbar_config = self.config.get(f"toolbar_{toolbar_name}")
            last_elem = toolbar_config[-1] if isinstance(toolbar_config, list) and len(toolbar_config) else []
            if "Source" not in last_elem:
                last_elem.append("Source")
            if "Language" not in last_elem:
                last_elem.append("Language")


class CKEditorWidget(CKEditorMixin, BaseCKEditorWidget):
    pass


class CKEditorUploadingWidget(CKEditorMixin, BaseCKEditorUploadingWidget):
    pass


class RichTextUploadingFormField(fields.CharField):
    def __init__(
        self,
        config_name="default",
        extra_plugins=None,
        external_plugin_resources=None,
        *args,
        **kwargs,
    ):
        kwargs.update(
            {
                "widget": CKEditorUploadingWidget(
                    config_name=config_name,
                    extra_plugins=extra_plugins,
                    external_plugin_resources=external_plugin_resources,
                )
            }
        )
        super().__init__(*args, **kwargs)


class RichTextUploadingField(BaseRichTextUploadingField):
    @staticmethod
    def _get_form_class():
        return RichTextUploadingFormField


def optgroups(data, selected):
    optgroups = f"<option selected value>{_('Select')}</option>\n"
    for k, v in data.items():
        if k == "":
            optgroups += make_html_options(v, selected, with_first=False)
        else:
            optgroups += f'<optgroup label="{_(k)}">\n'
            optgroups += make_html_options(v, selected, with_first=False)
            optgroups += "</optgroup>\n"
    return optgroups


def make_html_options(pairs, selected="", with_first=True):
    options_tmp = '<option value="{}" title="{}" {} data-animation=true>{}</option>\n'
    if with_first:
        options = f"<option disabled selected value>{_('Select')}</option>\n"
    else:
        options = ""
    for pair in pairs:
        if pair[0] == selected:
            options += options_tmp.format(pair[0], pair[2], "selected", pair[1])
        elif pair[0] == "-":
            options += "<option disabled></option>\n"
        else:
            options += options_tmp.format(pair[0], pair[2], "", pair[1])
    return options


def make_row(cols, row):
    _result = [getattr(row, col) for col in cols]
    return [(x.repr if x.repr is not None else "") if hasattr(x, "repr") else x or "" for x in _result]


def read(instance, limit=8):
    data = []
    try:
        rows = mit.seekable(instance.data.iter(size=limit, sort="row_no"))
        rows.seek(0)
        column_names = instance.data.headers_map.keys()
        for count, row in enumerate(rows, start=1):
            data.append(make_row(column_names, row))
            if count == limit:
                break
    except Exception:
        pass
    return data


class JsonPairInputsWidget(Widget):
    def __init__(self, *args, **kwargs):
        """
        kwargs:
        key_attrs -- html attributes applied to the 1st input box pairs
        val_attrs -- html attributes applied to the 2nd input box pairs

        """
        self.key_attrs = {}
        self.val_attrs = {}
        if "key_attrs" in kwargs:
            self.key_attrs = kwargs.pop("key_attrs")
        if "val_attrs" in kwargs:
            self.val_attrs = kwargs.pop("val_attrs")
        super().__init__(*args, **kwargs)


class JsonPairDatasetInputs(JsonPairInputsWidget):

    def render(self, name, value, attrs=None, renderer=None):
        """Renders this widget into an html string

        args:
        name  (str)  -- name of the field
        value (str)  -- a json string of a two-tuple list automatically passed in by django
        attrs (dict) -- automatically passed in by django (unused in this function)
        """
        twotuple = json.loads(value)
        if not twotuple:
            twotuple = {}
            twotuple["key"] = "value"

        ret = ""
        if value and len(value) > 0:
            for k, v in twotuple.items():
                key, value = _(k), v

                key_input = f'<input type="text" name="json_key[{name}]" value="{key}">'
                val_input = f'<input type="text" name="json_value[{name}]" value="{value}" class="customfields"><br>'

                ret += key_input + val_input
        return mark_safe(ret)

    def value_from_datadict(self, data, files, name):
        """
        Returns the simplejson representation of the key-value pairs
        sent in the POST parameters

        args:
        data  (dict)  -- request.POST or request.GET parameters
        files (list)  -- request.FILES
        name  (str)   -- the name of the field associated with this widget

        """

        customfields = {}
        if ("json_key[%s]" % name) in data and ("json_value[%s]" % name) in data:
            keys = data.getlist("json_key[%s]" % name)
            values = data.getlist("json_value[%s]" % name)
            for key, value in zip(keys, values):
                if len(key) > 0 and key != "key":
                    customfields[key] = value
        return json.dumps(customfields)

    class Media:

        js = ("admin/js/widgets/customfields.js",)
        css = {"all": ("admin/css/customfields.css",)}


class ResourceDataRulesWidget(JsonPairInputsWidget):

    def render(self, name, value, attrs=None, renderer=None):
        self.value = json.loads(value) if value else {}
        data = json.loads(value) if value else {}
        if data:
            data = data.get("fields", [])
            selects = []
            headers = []
            fields = []
            for i, column in enumerate(data):
                column_type = column.get("type")
                column_type_input = _(column_type)

                selects.append([make_html_options(settings.VERIFICATION_RULES), i])
                fields.append(column_type_input)
                headers.append(column.get("name", ""))

            data = read(self.instance)

            html = get_template("widgets/resource_data_rules.html").render(
                {"data": data, "selects": selects, "headers": headers, "fields": fields}
            )

            return mark_safe(html)

    def value_from_datadict(self, data, files, name):

        schema = self.instance.tabular_data_schema
        return json.dumps(schema)


class ResourceDataSchemaWidget(JsonPairInputsWidget):

    def render(self, name, value, attrs=None, renderer=None):
        self.value = json.loads(value) if value else {}
        data = json.loads(value) if value else {}
        if data:
            data = data.get("fields", [])
            selects = []
            headers = []
            for i, column in enumerate(data):
                column_type = column.get("type")

                selects.append([make_html_options(settings.DATA_TYPES, column_type), i])
                headers.append(column.get("name", ""))

            data = read(self.instance)

            html = get_template("widgets/resource_data_types.html").render(
                {
                    "data": data,
                    "selects": selects,
                    "headers": headers,
                }
            )

            return mark_safe(html)

    def value_from_datadict(self, data, files, name):
        schema = self.instance.tabular_data_schema
        _data = {int(k.replace("schema_type_", "")): v for k, v in data.items() if k.startswith("schema_type_")}
        for k, v in _data.items():
            schema["fields"][k]["type"] = v
            if v in ["date", "datetime", "time"] and schema["fields"][k]["format"] == "default":
                schema["fields"][k]["format"] = "any"
            # The format keyword options for `string` are `default`, `email`, `uri`, `binary`, and `uuid`.
            if v == "string" and schema["fields"][k]["format"] == "any":
                schema["fields"][k]["format"] = "default"
        return json.dumps(schema)


class ResourceMapsAndPlotsWidget(JsonPairInputsWidget):

    def render(self, name, value, attrs=None, renderer=None):
        self.value = json.loads(value) if value else {}
        data = json.loads(value) if value else {}
        if data:
            data = data.get("fields", [])
            selects = []
            headers = []
            for i, column in enumerate(data):
                column_geo = column.get("geo")
                selects.append([optgroups(settings.GEO_TYPES, column_geo), i])
                headers.append(column.get("name", ""))

            data = read(self.instance)

            html = get_template("widgets/resource_maps_and_plots.html").render(
                {
                    "data": data,
                    "selects": selects,
                    "headers": headers,
                }
            )
            return mark_safe(html)

    def value_from_datadict(self, data, files, name):

        schema = self.instance.tabular_data_schema or {}
        if schema:
            schema["geo"] = {}
            for k, v in data.items():
                if k.startswith("geo_"):
                    index = int(k.replace("geo_", ""))

                    if v:
                        schema["fields"][index]["geo"] = v
                        schema["geo"][v] = {
                            "col_name": schema["fields"][index]["name"],
                            "col_index": index,
                        }

                    else:
                        if "geo" in schema["fields"][index]:
                            del schema["fields"][index]["geo"]
        return json.dumps(schema)


class ExternalDatasetsWidget(JsonPairDatasetInputs):
    template_name = "widgets/external_datasets.html"

    def __init__(self, *args, **kwargs):
        kwargs["val_attrs"] = {"size": 35}
        kwargs["key_attrs"] = {"class": "large"}
        super().__init__(*args, **kwargs)

    def render(self, name, value, attrs=None, renderer=None):
        """Render the widget as an HTML string."""
        context = self.get_context(name, value, attrs)
        return self._render(self.template_name, context, renderer)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["items_list"] = json.loads(value) or [{"url": "", "title": ""}]
        return context

    def value_from_datadict(self, data, files, name):
        result = []
        if "json_key[customfields]" in data and "json_value[customfields]" in data:
            titles = data.getlist("json_key[customfields]")
            urls = data.getlist("json_value[customfields]")
            for title, url in zip(titles, urls):
                if len(title) > 0 and title != "key":
                    result.append({"title": title, "url": url})
        return json.dumps(result)

    class Media:
        extend = False
        css = {"all": ("admin/css/customfields.css",)}


MAX_OPENNESS_SCORE = 5


class OpennessScoreStars(Widget):
    """
    Renders openness score (int) as stars, analogous to how frontend does in the star-rating-component.
    Input value is an int (Resource.openness_score). To simplify the template we also pass a list[bool],
    such that the number of True's in it represents openness score.

    Inspired by https://github.com/ckan/ckanext-qa/blob/master/ckanext/qa/templates/qa/stars.html
    """

    template_name = "admin/forms/widgets/resources/openness-score-stars.html"

    def get_context(self, name: str, value: int, attrs: Dict[str, Any]) -> Dict[str, str]:
        context = super().get_context(name, value, attrs)
        context["openness_score_value"] = value
        context["stars_list"] = self._score_as_list(value)
        context["max_stars"] = MAX_OPENNESS_SCORE
        return context

    @staticmethod
    def _score_as_list(value: int, max_value: int = MAX_OPENNESS_SCORE) -> List[bool]:
        v = max(0, min(max_value, value))
        return [True] * v + [False] * (max_value - v)
