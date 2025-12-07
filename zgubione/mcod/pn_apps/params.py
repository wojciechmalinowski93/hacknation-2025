import param
from django.utils.translation import gettext as _

from mcod.organizations.models import Organization
from mcod.pn_apps.widgets import BootstrapSelectWidget, ExtendedRadioButtonGroup
from mcod.resources.models import RESOURCE_TYPE


class BaseStatsParamWidget:
    param_cls = param.String  # noqa
    widget_cls = None

    def __init__(self, name, **kwargs):
        self.alt_title = name
        _params = self.widget_default_params
        _params.update(kwargs)
        self.widget_params = _params

    @property
    def widget_default_params(self):
        return {}

    @property
    def param_kwargs(self):
        return {}

    @property
    def param(self):
        return self.param_cls(**self.param_kwargs)

    @property
    def widget(self):
        if self.widget_cls:
            self.widget_params["type"] = self.widget_cls
        self.widget_params["alt_title"] = self.alt_title
        return self.widget_params


class MultiSelectParamWidget(BaseStatsParamWidget):
    param_cls = param.ListSelector
    widget_cls = BootstrapSelectWidget

    @property
    def param_kwargs(self):
        return {"objects": self.widget_objects}

    @property
    def widget_objects(self):
        return []


class QuerysetMultiSelectParamWidget(MultiSelectParamWidget):
    model = None

    def __init__(self, query_params=None, **kwargs):
        self.query_params = query_params
        super().__init__(**kwargs)

    def get_queryset(self):
        if self.query_params:
            qs = self.model.objects.filter(self.query_params)
        else:
            qs = self.model.objects.all()
        return qs


class UserGroupProvidersParamsWidget(QuerysetMultiSelectParamWidget):
    model = Organization

    @property
    def widget_default_params(self):
        return {
            "actions_box": False,
            "live_search": True,
            "selected_text_format": "count > 3",
            "none_selected_text": "Nie wybrano żadnej instytucji",
            "none_results_text": "Nie znaleziono instytucji dla frazy {0}",
            "count_selected_text": "{0} z {1} instytucji",
        }

    @property
    def widget_objects(self):
        def make_abbreviation(title, abbr=None):
            if not abbr:
                abbr = "".join(wrd[0] for wrd in title.split())
            return abbr

        return {
            title: (id, make_abbreviation(title, abbr))
            for id, title, abbr in self.get_queryset().values_list("id", "title", "abbreviation")
        }


class ResourceTypeParamWidget(MultiSelectParamWidget):

    def __init__(self, **kwargs):
        super().__init__(_("Type of data"), **kwargs)

    @property
    def widget_default_params(self):
        return {
            "show_labels": False,
            "actions_box": False,
            "live_search": False,
            "selected_text_format": "count > 2",
            "none_selected_text": _("No data type was selected"),
            "count_selected_text": _("{0} of {1} data types"),
        }

    @property
    def widget_objects(self):
        return {str(item[1]): (item[0], "") for item in RESOURCE_TYPE}


class TimePeriodParamWidget(BaseStatsParamWidget):
    param_cls = param.Selector
    widget_cls = ExtendedRadioButtonGroup

    def __init__(self, **kwargs):
        super().__init__(_("Period"), **kwargs)

    @property
    def param_kwargs(self):
        return {"objects": self.widget_objects, "default": "month"}

    @property
    def widget_objects(self):
        return {
            _("Month"): "month",
            _("Quarter"): "quarter",
            _("Year"): "year",
        }


class VizTypeParamWidget(MultiSelectParamWidget):

    def __init__(self, **kwargs):
        super().__init__(_("Visualization type"), **kwargs)

    @property
    def widget_default_params(self):
        return {
            "show_labels": False,
            "actions_box": False,
            "live_search": False,
            "selected_text_format": "count > 2",
            "none_selected_text": _("No type of visualization has been selected"),
            "count_selected_text": _("{0} of {1} visualization types"),
        }

    @property
    def widget_objects(self):
        return {
            _("Table"): ("ct_table", ""),
            _("Map"): ("ct_map", ""),
            _("Chart"): ("ct_chart", ""),
            _("No visualization"): ("ct_none", ""),
        }


class PresentationTypeParamWidget(BaseStatsParamWidget):
    param_cls = param.Selector
    widget_cls = ExtendedRadioButtonGroup

    def __init__(self, **kwargs):
        super().__init__(_("Way of presentation"), **kwargs)

    @property
    def param_kwargs(self):
        return {"objects": self.widget_objects, "default": "absolute"}

    @property
    def widget_objects(self):
        return {
            _("Number"): "absolute",
            _("Percent"): "percentage",
        }
