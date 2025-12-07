import json
import logging
from collections import OrderedDict
from datetime import date
from functools import partial
from time import time

import holoviews as hv
import hvplot.pandas  # noqa
import numpy as np
import pandas as pd
import panel as pn
from dateutil import relativedelta
from django.conf import settings
from django.db.models import (
    Case,
    CharField,
    Count,
    Exists,
    F,
    FloatField,
    IntegerField,
    OuterRef,
    Q,
    Subquery,
    Sum,
    When,
)
from django.db.models.functions import Cast, Coalesce, Trunc
from django.utils.translation import activate, gettext as _
from user_agents import parse

from mcod.categories.models import Category
from mcod.counters.models import ResourceDownloadCounter, ResourceViewCounter
from mcod.datasets.models import Dataset
from mcod.organizations.models import Organization
from mcod.pn_apps.base import (
    ChartPanel,
    DataCountByTimePeriodForGroup,
    NewDataByTimePeriodForGroup,
    RankingPanel,
    StatsPanel,
)
from mcod.pn_apps.mixins import CombinedChartMixin, UserFilterMixin, UserOrganizationGroupMixin
from mcod.pn_apps.params import (
    PresentationTypeParamWidget,
    ResourceTypeParamWidget,
    TimePeriodParamWidget,
    UserGroupProvidersParamsWidget,
    VizTypeParamWidget,
)
from mcod.pn_apps.utils import (
    format_time_period,
    prepare_time_periods,
    register_event_widgets,
    set_locale,
)
from mcod.resources.models import Resource
from mcod.searchhistories.models import SearchHistory
from mcod.tags.models import Tag
from mcod.watchers.models import Subscription

pd.options.plotting.backend = "holoviews"

hv.extension("bokeh", logo=False)

types_map = {
    "api": "API",
    "website": _("Web Site"),
    "file": _("File"),
    "all": _("Number of data"),
    "all_percentage": _("Percent od data"),
}

profile_log = logging.getLogger("stats-profile")


class Top10ProvidersByResourcesCount(RankingPanel):
    """
    Ranking instytucji o największej liczbie danych z podziałem na typ danych
    """

    widgets_cls = {"restypes": ResourceTypeParamWidget}
    model = Organization
    variable_widget = "restypes"

    def has_perm(self):
        perms = (self.user.is_superuser, self.user.is_editor, self.user.agent)

        return any(perms)

    def get_queryset(self):
        _Q = partial(
            Q,
            ("datasets__resources__status", "published"),
            ("datasets__resources__is_removed", False),
        )

        annotate = {}
        restypes = self.restypes or []
        _fs = None

        for rt, i in restypes:
            _f = Q(datasets__resources__type=rt)
            key = f"ct_{rt}"
            annotate[key] = Count("datasets__resources", filter=_Q().add(_f, Q.AND))

            if not _fs:
                _fs = _f
            else:
                _fs.add(_f, Q.OR)

        ct_total = Count("datasets__resources", filter=_Q())

        if _fs:
            ct_total.filter.add(_fs, Q.AND)
        annotate["ct_total"] = ct_total

        return super().get_queryset().annotate(**annotate).order_by("-ct_total")

    def get_dataframe(self):
        results = self.get_results()
        restypes = self.restypes or []
        data = {}
        for j, inst in enumerate(results):
            idx = data.setdefault(_("Entry"), [])
            idx.append(j + 1)
            p = data.setdefault("Nazwa dostawcy", [])
            p.append(inst.title)
            if restypes:
                for _rt, _z in restypes:
                    val = getattr(inst, f"ct_{_rt}", 0)
                    i = data.setdefault(types_map[_rt], [])
                    i.append(val)
            else:
                m = data.setdefault(types_map["all"], [])
                m.append(inst.ct_total)

        df = pd.DataFrame(data=data)
        df.set_index(_("Entry"), inplace=True)
        return df

    def chart(self):
        chart = self.cached_df.hvplot.bar(use_index=True, **self.get_bar_kwargs())
        chart.opts(xlabel="", axiswise=True)
        return chart


class Top10MostDownloadedDatasets(RankingPanel):
    """
    Ranking zbiorów o największej liczbie pobrań'
    """

    model = Dataset

    def has_perm(self):
        perms = (self.user.is_authenticated,)

        return any(perms)

    def get_queryset(self):
        qs = (
            ResourceDownloadCounter.objects.filter(
                resource__dataset__status="published",
                resource__dataset__is_removed=False,
                resource__dataset__is_permanently_removed=False,
            )
            .values("resource__dataset__title")
            .annotate(downloads_count=Coalesce(Sum("count"), 0))
            .annotate(title_i18n=F("resource__dataset__title_i18n"))
            .order_by("-downloads_count")
        )
        return qs.values("title_i18n", "downloads_count")

    def get_dataframe(self):
        results = self.get_results()
        data = {}
        for _i, inst in enumerate(results):
            idx = data.setdefault(_("Entry"), [])
            idx.append(_i + 1)
            n = data.setdefault(_("Dataset"), [])
            n.append(inst["title_i18n"])
            i = data.setdefault(_("Downloads"), [])
            i.append(inst["downloads_count"])
        if not data:
            data[_("Entry")] = [1]
            data[_("Dataset")] = [_("None")]
            data[_("Downloads")] = [0]

        df = pd.DataFrame(data)
        df.set_index(_("Entry"), inplace=True)
        return df

    def init_labels(self):
        self.index_label = ""
        self.y_axis_label = _("Downloads")
        self.x_axis_label = _("Dataset")


class Top10MostViewedDatasets(RankingPanel):
    """
    Ranking zbiorów o największej popularności (liczbie odsłon)
    """

    model = Dataset

    def has_perm(self):
        perms = (self.user.is_authenticated,)

        return any(perms)

    def get_queryset(self):
        qs = (
            ResourceViewCounter.objects.filter(
                resource__dataset__status="published",
                resource__dataset__is_removed=False,
                resource__dataset__is_permanently_removed=False,
            )
            .values("resource__dataset__title")
            .annotate(views_count=Coalesce(Sum("count"), 0))
            .annotate(title_i18n=F("resource__dataset__title_i18n"))
        )
        return qs.order_by("-views_count").values("views_count", "title_i18n")

    def get_dataframe(self):
        results = self.get_results()
        data = {}
        for _i, inst in enumerate(results):
            idx = data.setdefault(_("Entry"), [])
            idx.append(_i + 1)
            n = data.setdefault(_("Dataset"), [])
            n.append(inst["title_i18n"])
            i = data.setdefault(_("Views"), [])
            i.append(inst["views_count"])
        if not data:
            data[_("Entry")] = [1]
            data[_("Dataset")] = [_("None")]
            data[_("Views")] = [0]

        df = pd.DataFrame(data=data)
        df.set_index(_("Entry"), inplace=True)

        return df

    def chart(self):
        chart = self.cached_df.hvplot.bar(use_index=True, **self.get_bar_kwargs())

        chart.opts(xlabel="", axiswise=True)
        return chart


class Top10ProvidersByDatasetsCount(RankingPanel):
    """
    Ranking instytucji o największej liczbie zbiorów danych w podziale na rodzaj wizualizacji (TOP10)
    """

    model = Organization
    widgets_cls = {
        "viztypes": VizTypeParamWidget,
    }
    variable_widget = "viztypes"

    def has_perm(self):
        perms = (self.user.is_superuser, self.user.is_editor, self.user.agent)
        return any(perms)

    def get_queryset(self):
        _Q = partial(
            Q,
            ("datasets__status", "published"),
            ("datasets__is_removed", False),
        )

        annotate = {}
        viztypes = self.viztypes or []

        _fs = None
        for viz, i in viztypes:
            if viz == "ct_table":
                _f = Q(datasets__resources__has_table=True)
            elif viz == "ct_chart":
                _f = Q(datasets__resources__has_chart=True)
            elif viz == "ct_map":
                _f = Q(datasets__resources__has_map=True)
            else:
                _f = Q(
                    datasets__resources__has_table=False,
                    datasets__resources__has_chart=False,
                    datasets__resources__has_map=False,
                )
            annotate[viz] = Count("datasets__pk", filter=_Q().add(_f, Q.AND), distinct=True)

            if not _fs:
                _fs = _f
            else:
                _fs.add(_f, Q.OR)

        ct_total = Count("datasets__pk", filter=_Q(), distinct=True)
        if _fs:
            ct_total.filter.add(_fs, Q.AND)
        annotate["ct_total"] = ct_total

        return super().get_queryset().annotate(**annotate).order_by("-ct_total")

    def get_dataframe(self):
        results = self.get_results()

        viztypes = self.viztypes or []
        selectedVizTypes = list(filter(lambda elem: elem[1] in viztypes, self.param.viztypes.names.items()))

        data = {}
        for _i, inst in enumerate(results):
            idx = data.setdefault(_("Entry"), [])
            idx.append(_i + 1)
            p = data.setdefault("Nazwa dostawcy", [])
            p.append(inst.title)
            if viztypes:
                for key, val in selectedVizTypes:
                    m = data.setdefault(key, [])
                    num = getattr(inst, val[0]) or 0
                    m.append(num)
            else:
                m = data.setdefault("Liczba zbiorów", [])
                m.append(inst.ct_total)

        df = pd.DataFrame(data=data)
        df.set_index(_("Entry"), inplace=True)

        return df

    def chart(self):
        chart = self.cached_df.hvplot.bar(use_index=True, **self.get_bar_kwargs())
        chart.opts(xlabel="", axiswise=True)

        return chart


class DatasetsCountByTimePeriod(StatsPanel):
    """
    Liczba zbiorów danych w podziale na miesiące/kwartały/lata i rodzaj wizualizacji
    """

    model = Dataset

    widgets_cls = {
        "timeperiod": TimePeriodParamWidget,
        "viztypes": VizTypeParamWidget,
    }
    show_table_index = False
    show_initial_table = False
    variable_widget = "viztypes"

    def has_perm(self):
        perms = (self.user.is_authenticated,)

        return any(perms)

    def get_queryset(self):
        qs = super().get_queryset()
        viz_types_dict = {
            "ct_table": Resource.objects.filter(dataset=OuterRef("pk"), has_table=True),
            "ct_chart": Resource.objects.filter(dataset=OuterRef("pk"), has_chart=True),
            "ct_map": Resource.objects.filter(dataset=OuterRef("pk"), has_map=True),
            "ct_none": Resource.objects.filter(dataset=OuterRef("pk"), has_map=False, has_chart=False, has_table=False),
        }
        if self.viztypes:
            selected_types = {v_type[0]: Exists(viz_types_dict[v_type[0]]) for v_type in self.viztypes}
        else:
            selected_types = {}
        qs = qs.annotate(**selected_types)
        count_filter = None
        single_type_counts = {}
        for selected_type in selected_types.keys():
            type_query = Q(**{selected_type: True})
            type_name = selected_type.split("_")[1]
            if not count_filter:
                count_filter = type_query
            else:
                count_filter |= type_query
            single_type_counts[f"{type_name}_count"] = Count("pk", filter=type_query)
        overall_count_expr = Count("pk", filter=count_filter, distinct=True) if count_filter else Count("pk")
        all_annotations = {"dataset_count": overall_count_expr}
        all_annotations.update(single_type_counts)
        return (
            qs.annotate(period=Trunc("created", kind=self.timeperiod))
            .values("period")
            .annotate(**all_annotations)
            .order_by("period")
            .values("dataset_count", "period", *list(single_type_counts.keys()))
        )

    def get_dataframe(self):
        qs = self.get_results()

        periods = prepare_time_periods(qs[0]["period"], qs[-1]["period"], self.timeperiod)

        viztypes = self.viztypes or []
        selectedVizTypes = list(filter(lambda elem: elem[1] in viztypes, self.param.viztypes.names.items()))

        if viztypes:
            viz_dicts = {viz_label[0]: 0 for viz_label in selectedVizTypes}
        else:
            viz_dicts = {_("Number"): 0}

        _data = OrderedDict({itm: {_("Entry"): i, "values": dict(**viz_dicts)} for i, itm in enumerate(periods)})

        for item in qs:
            period = format_time_period(item["period"], self.timeperiod)
            if viztypes:
                for key, val in selectedVizTypes:
                    count_key = val[0].split("_")[1]
                    _data[period]["values"][key] = item.get(f"{count_key}_count", 0)
            else:
                _data[period]["values"][_("Number")] = item["dataset_count"]
        values_dict = {viz: [] for viz in viz_dicts.keys()}
        data = {_("Entry"): [], _("Period"): []}
        data.update(values_dict)
        for period, period_details in _data.items():
            data[_("Entry")].append(period_details[_("Entry")])
            data[_("Period")].append(period)
            for value_label, value in period_details["values"].items():
                data[value_label].append(value)

        df = pd.DataFrame(data=data)
        df.set_index(_("Entry"), inplace=True)
        for label_name in viz_dicts.keys():
            df[label_name] = df[label_name].cumsum()
        return df

    def chart(self):
        chart = self.cached_df.plot.bar(stacked=True, legend="bottom", x=_("Period"), **self.get_chart_kwargs())

        chart.opts(xlabel="", xrotation=90, axiswise=True)
        return chart


class ResourcesCountByTimePeriod(StatsPanel):
    """
    Liczba danych w podziale na miesiące/kwartały/lata oraz typ danych
    """

    model = Resource
    widgets_cls = {
        "timeperiod": TimePeriodParamWidget,
        "restypes": ResourceTypeParamWidget,
    }
    show_table_index = False
    show_initial_table = False
    variable_widget = "restypes"

    def has_perm(self):
        perms = (self.user.is_superuser, self.user.is_editor, self.user.agent)

        return any(perms)

    def get_queryset(self):
        qs = super().get_queryset().annotate(period=Trunc("created", kind=self.timeperiod)).values("period")
        rtc = Count("type")
        res_types = [itm[0] for itm in self.restypes] if self.restypes else []
        values = ["period", "num"]
        if res_types:
            rtc.filter = Q(type__in=res_types)
            values.append("type")

        return qs.annotate(num=rtc).values(*values).order_by("period")

    def get_dataframe(self):
        qs = self.get_results()

        periods = prepare_time_periods(qs[0]["period"], qs[-1]["period"], self.timeperiod)
        res_types = [itm[0] for itm in self.restypes] if self.restypes else []
        _res_types = res_types or ["all"]

        _data = OrderedDict()
        for i, itm in enumerate(periods):
            val = {res_type: 0 for res_type in _res_types}
            val[_("Entry")] = i
            _data[itm] = val

        for itm in qs:
            period = format_time_period(itm["period"], self.timeperiod)
            num_key = itm["type"] if res_types else "all"
            _data[period][num_key] = itm["num"]

        data = {}
        data[_("Entry")] = [i[_("Entry")] for i in _data.values()]
        data[_("Period")] = list(_data.keys())
        for rt in _res_types:
            data[types_map[rt]] = [i[rt] for i in _data.values()]

        df = pd.DataFrame(data=data)
        df.set_index(_("Entry"), inplace=True)
        for rt in _res_types:
            k = types_map[rt]
            df[k] = df[k].cumsum()

        for rt in _res_types:
            df = df[df[types_map[rt]] > 0]

        return df

    def chart(self):
        chart = self.cached_df.plot.bar(stacked=True, legend="bottom", x=_("Period"), **self.get_chart_kwargs())
        chart.opts(
            xlabel="",
            xrotation=90,
            axiswise=True,
        )
        return chart


class NewDatasetsCountByTimePeriod(StatsPanel):
    """
    Liczba nowych zbiorów danych w podziale na miesiące/kwartały/lata i typ wizualizacji
    """

    model = Dataset
    widgets_cls = {
        "timeperiod": TimePeriodParamWidget,
        "viztypes": VizTypeParamWidget,
        "presentation_type": PresentationTypeParamWidget,
    }

    show_table_index = False
    show_initial_table = False
    variable_widget = "viztypes"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.p_map = {
            "absolute": _("Number"),
            "percentage": _("Percent"),
        }

    def has_perm(self):
        perms = (self.user.is_authenticated,)

        return any(perms)

    @property
    def value_dim_label(self):
        return self.p_map[self.presentation_type]

    def get_queryset(self):
        qs = super().get_queryset()
        viz_types_dict = {
            "ct_table": Resource.objects.filter(dataset=OuterRef("pk"), has_table=True),
            "ct_chart": Resource.objects.filter(dataset=OuterRef("pk"), has_chart=True),
            "ct_map": Resource.objects.filter(dataset=OuterRef("pk"), has_map=True),
            "ct_none": Resource.objects.filter(dataset=OuterRef("pk"), has_map=False, has_chart=False, has_table=False),
        }
        selected_types = {}
        if self.viztypes:
            selected_types = {v_type[0]: Exists(viz_types_dict[v_type[0]]) for v_type in self.viztypes}
            qs = qs.annotate(**selected_types)
        count_filter = None
        single_type_counts = {}
        for selected_type in selected_types.keys():
            type_query = Q(**{selected_type: True})
            type_name = selected_type.split("_")[1]
            if not count_filter:
                count_filter = type_query
            else:
                count_filter |= type_query
            single_type_counts[f"{type_name}_count"] = Count("pk", filter=type_query)
        overall_count_expr = Count("pk", filter=count_filter, distinct=True) if count_filter else Count("pk")
        all_annotations = {"dataset_count": overall_count_expr}
        all_annotations.update(single_type_counts)
        return (
            qs.annotate(period=Trunc("created", kind=self.timeperiod))
            .values("period")
            .annotate(**all_annotations)
            .order_by("period")
            .values("period", "dataset_count", *list(single_type_counts.keys()))
        )

    def get_dataframe(self):
        qs = self.get_results()
        viztypes = self.viztypes or []
        periods = prepare_time_periods(qs[0]["period"], qs[-1]["period"], self.timeperiod)
        selectedVizTypes = list(filter(lambda elem: elem[1] in viztypes, self.param.viztypes.names.items()))

        if viztypes:
            viz_dicts = {viz_label[0]: 0 for viz_label in selectedVizTypes}
        else:
            viz_dicts = {self.p_map[self.presentation_type]: 0}
        _data = OrderedDict({itm: {_("Entry"): i, "values": dict(**viz_dicts)} for i, itm in enumerate(periods)})
        for item in qs:
            period = format_time_period(item["period"], self.timeperiod)
            if viztypes:
                for key, val in selectedVizTypes:
                    count_key = val[0].split("_")[1]
                    num = item.get(f"{count_key}_count", 0)
                    _data[period]["values"][key] = num
            else:
                num = item["dataset_count"]
                _data[period]["values"][self.p_map[self.presentation_type]] = num
        values_dict = {viz: [] for viz in viz_dicts.keys()}
        data = {_("Entry"): [], _("Period"): []}
        data.update(values_dict)
        for period, period_details in _data.items():
            data[_("Entry")].append(period_details[_("Entry")])
            data[_("Period")].append(period)
            for value_label, value in period_details["values"].items():
                data[value_label].append(value)

        df = pd.DataFrame(data=data)
        if self.presentation_type == "percentage":
            for v_key in viz_dicts.keys():
                df[f"{v_key}_cumsum"] = df[v_key].shift().cumsum()
                df[f"{v_key}_cumsum"] = df[f"{v_key}_cumsum"].fillna(0)
                df[v_key] = np.where(
                    df[f"{v_key}_cumsum"] == 0,
                    0,
                    (df[v_key] / df[f"{v_key}_cumsum"]) * 100,
                )
                df[v_key] = df[v_key].round(2)
                del df[f"{v_key}_cumsum"]
        df.set_index(_("Entry"), inplace=True)

        return df

    def chart(self):
        chart = self.cached_df.plot.bar(stacked=True, legend="bottom", x=_("Period"), **self.get_chart_kwargs())

        chart.opts(xlabel="", xrotation=90, axiswise=True)
        return chart


class NewResourcesCountByTimePeriod(StatsPanel):
    """
    Liczba nowych danych w podziale na miesiące/kwartały/lata i typ danych
    """

    model = Resource
    widgets_cls = {
        "timeperiod": TimePeriodParamWidget,
        "restypes": ResourceTypeParamWidget,
        "presentation_type": PresentationTypeParamWidget,
    }
    show_table_index = False
    show_initial_table = False
    variable_widget = "restypes"
    p_map = {
        "absolute": "Liczba danych",
        "percentage": "Procent danych",
    }

    @property
    def value_dim_label(self):
        return self.p_map[self.presentation_type]

    def has_perm(self):
        perms = (self.user.is_superuser, self.user.is_editor, self.user.agent)

        return any(perms)

    def get_queryset(self):
        qs = super().get_queryset()
        period_grouped_qs = qs.annotate(period=Trunc("created", kind=self.timeperiod)).values("period")
        rtc = Count("type")
        res_types = [itm[0] for itm in self.restypes] if self.restypes else []
        values = ["period", "num"]
        if res_types:
            rtc.filter = Q(type__in=res_types)
            values.append("type")
        return period_grouped_qs.annotate(num=rtc).values(*values).order_by("period")

    def get_dataframe(self):
        qs = self.get_results()

        periods = prepare_time_periods(qs[0]["period"], qs[-1]["period"], self.timeperiod)
        res_types = [itm[0] for itm in self.restypes] if self.restypes else []
        all_label = "all"
        if self.presentation_type == "percentage":
            all_label = "all_percentage"
        _res_types = res_types or [all_label]

        _data = OrderedDict()
        for i, itm in enumerate(periods):
            val = {res_type: 0 for res_type in _res_types}
            val[_("Entry")] = i
            _data[itm] = val

        for itm in qs:
            period = format_time_period(itm["period"], self.timeperiod)
            num_key = itm["type"] if res_types else all_label
            num = itm["num"]
            _data[period][num_key] = num

        data = {}
        data[_("Entry")] = [i[_("Entry")] for i in _data.values()]
        data[_("Period")] = list(_data.keys())
        for rt in _res_types:
            data[types_map[rt]] = [i[rt] for i in _data.values()]

        df = pd.DataFrame(data=data)
        if self.presentation_type == "percentage":
            for rt in _res_types:
                data_label = types_map[rt]
                df[f"{data_label}_cumsum"] = df[data_label].shift().cumsum()
                df[f"{data_label}_cumsum"] = df[f"{data_label}_cumsum"].fillna(0)
                df[data_label] = np.where(
                    df[f"{data_label}_cumsum"] == 0,
                    0,
                    (df[data_label] / df[f"{data_label}_cumsum"]) * 100,
                )
                df[data_label] = df[data_label].round(2)
                del df[f"{data_label}_cumsum"]
        df.set_index(_("Entry"), inplace=True)

        return df

    def chart(self):
        chart = self.cached_df.plot.bar(stacked=True, legend="bottom", x=_("Period"), **self.get_chart_kwargs())

        chart.opts(xlabel="", xrotation=90, axiswise=True)
        return chart


class Top10MostDownloadedResources(RankingPanel):
    """
    Ranking danych o największej liczbie pobrań
    """

    model = Resource
    y_axis_attr_name = "downloads_count"
    x_axis_attr_name = "title"

    def init_labels(self):
        super().init_labels()
        self.x_axis_label = "Dane"
        self.y_axis_label = "Liczba pobrań"

    def get_queryset(self):
        qs = (
            ResourceDownloadCounter.objects.filter(
                resource__dataset__status="published",
                resource__dataset__is_removed=False,
                resource__dataset__is_permanently_removed=False,
            )
            .annotate(title=F("resource__title"))
            .values("title")
            .annotate(downloads_count=Sum("count"))
        )
        return qs.values("title", "downloads_count").order_by("-downloads_count")


class Top10OrganizationsMostDownloadedDatasets(RankingPanel):
    """
    Ranking instytucji o największej liczbie pobrań
    """

    model = Organization
    y_axis_attr_name = "org_download_count"
    x_axis_attr_name = "title"

    def init_labels(self):
        super().init_labels()
        self.x_axis_label = "Instytucja"
        self.y_axis_label = "Liczba pobrań"

    def get_queryset(self):
        queryset = (
            ResourceDownloadCounter.objects.filter(
                resource__dataset__status="published",
                resource__dataset__is_removed=False,
                resource__dataset__is_permanently_removed=False,
            )
            .values("resource__dataset__organization__title")
            .annotate(org_download_count=Coalesce(Sum("count"), 0))
            .annotate(title=F("resource__dataset__organization__title"))
        )
        return queryset.order_by("-org_download_count").values("title", "org_download_count")


class ResourceOpennessReportChart(ChartPanel):
    """
    Liczba danych w podziale na stopień otwartości
    """

    model = Resource
    y_axis_attr_name = "openness_count"
    x_axis_attr_name = "openness_label"
    show_table_index = False
    use_index = True

    def init_labels(self):
        self.index_label = _("Openness level")
        self.x_axis_label = _("Openness level")
        self.y_axis_label = _("Number of data")

    def has_perm(self):
        perms = (self.user.is_authenticated,)

        return any(perms)

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.values("openness_score").annotate(openness_count=Count("openness_score")).order_by("-openness_count")
        return qs

    def get_dataframe(self):
        results = self.get_results()
        data = {}
        available_scores = set([r["openness_score"] for r in results])
        score_scale = set(range(0, 6))
        for score_data in results:
            n = data.setdefault(self.x_axis_label, [])
            n.append(_("Level {}").format(score_data["openness_score"]))
            i = data.setdefault(self.y_axis_label, [])
            i.append(score_data["openness_count"])
        missing_scores = score_scale.difference(available_scores)
        for score in missing_scores:
            n = data.setdefault(self.x_axis_label, [])
            n.append(_("Level {}").format(score))
            i = data.setdefault(self.y_axis_label, [])
            i.append(0)
        df = pd.DataFrame(data)
        df.index += 1
        return df

    def chart(self):
        chart = self.cached_df.hvplot.bar(**self.get_bar_kwargs())

        chart.opts(xlabel="", axiswise=True)
        return chart


class Top10MostPopularResources(RankingPanel):
    """
    Ranking danych o największej popularności
    """

    model = Resource
    x_axis_attr_name = "title"
    y_axis_attr_name = "views_count"

    def init_labels(self):
        super().init_labels()
        self.x_axis_label = "Dane"
        self.y_axis_label = "Liczba wyświetleń"

    def get_queryset(self):
        qs = (
            ResourceViewCounter.objects.filter(
                resource__status="published",
                resource__is_removed=False,
                resource__is_permanently_removed=False,
            )
            .values("resource__title")
            .annotate(views_count=Coalesce(Sum("count"), 0))
            .annotate(title=F("resource__title"))
        )
        return qs.values("title", "views_count").order_by("-views_count")


class Top10MostPopularOrganizations(RankingPanel):
    """
    Ranking instytucji o największej popularności
    """

    model = Organization
    x_axis_attr_name = "title"
    y_axis_attr_name = "views_sum"

    def init_labels(self):
        super().init_labels()
        self.x_axis_label = "Instytucja"
        self.y_axis_label = "Liczba wyświetleń"

    def get_queryset(self):
        qs = (
            ResourceViewCounter.objects.filter(
                resource__dataset__status="published",
                resource__dataset__is_removed=False,
                resource__dataset__is_permanently_removed=False,
            )
            .values("resource__dataset__organization__title")
            .annotate(views_sum=Coalesce(Sum("count"), 0))
            .annotate(title=F("resource__dataset__organization__title"))
        )
        return qs.order_by("-views_sum")


class TopResourceCountOrgfromGroup(UserFilterMixin, RankingPanel):
    """
    Ranking instytucji o największej liczbie danych w ramach swojej grupy instytucji
    """

    model = Resource
    x_axis_attr_name = "dataset__organization__title"
    y_axis_attr_name = "rtc_all"

    widgets_cls = {"restypes": ResourceTypeParamWidget}
    variable_widget = "restypes"

    def init_labels(self):
        super().init_labels()
        self.x_axis_label = "Instytucja"
        self.y_axis_label = "Liczba danych"

    def has_perm(self):
        perms = (self.user.agent,)

        return any(perms)

    def get_queryset(self):
        qs = super().get_queryset()
        if self.restypes:
            _r = [itm[0] for itm in self.restypes]
            qs = qs.filter(type__in=_r)
        annotates = {"rtc_all": Count("pk")}
        if self.restypes:
            _r = [itm[0] for itm in self.restypes]
            for _rt in _r:
                annotates[f"rtc_{_rt}"] = Count("pk", filter=Q(type=_rt))
        user_q = self.get_user_query("dataset__organization__agents__pk")
        qs = (
            qs.filter(
                user_q,
                dataset__is_removed=False,
                dataset__is_permanently_removed=False,
                dataset__status="published",
                dataset__organization__is_removed=False,
                dataset__organization__is_permanently_removed=False,
                dataset__organization__status="published",
            )
            .values("dataset__organization_id")
            .annotate(**annotates)
        )
        return qs.order_by("-rtc_all").values(
            "dataset__organization__title",
            "dataset__organization_id",
            *annotates.keys(),
        )

    def get_dataframe(self):
        results = self.get_results()
        data = {}
        org_ids = [result["dataset__organization_id"] for result in results]
        restypes = self.restypes or [("all", "")]
        for _i, inst in enumerate(results):
            idx = data.setdefault(_("Entry"), [])
            idx.append(_i + 1)
            p = data.setdefault(self.x_axis_label, [])
            p.append(inst[self.x_axis_attr_name])

            for _rt in restypes:
                val = inst.get(f"rtc_{_rt[0]}", 0)
                i = data.setdefault(types_map[_rt[0]], [])
                i.append(val)
        user_q = self.get_user_query("agents__pk")
        org_names = Organization.objects.filter(user_q).exclude(pk__in=org_ids).values_list("title", flat=True).order_by("-pk")
        left_orgs = self.top_count - len(org_ids)
        if left_orgs > 0:
            left_orgs = min(left_orgs, len(org_names))
            for _i, org_name in enumerate(org_names[:left_orgs], start=len(data.get(_("Entry"), []))):
                idx = data.setdefault(_("Entry"), [])
                idx.append(_i + 1)
                p = data.setdefault(self.x_axis_label, [])
                p.append(org_name)

                for _rt in restypes:
                    i = data.setdefault(types_map[_rt[0]], [])
                    i.append(0)
        if not org_names and not org_ids:
            data[_("Entry")] = [1]
            data[self.x_axis_label] = [_("None")]
            for _rt in restypes:
                i = data.setdefault(types_map[_rt[0]], [])
                i.append(0)

        df = pd.DataFrame(data=data)
        df.set_index(_("Entry"), inplace=True)
        return df

    def chart(self):
        chart = self.cached_df.plot.bar(**self.get_bar_kwargs())

        chart.opts(xlabel="", axiswise=True)
        return chart


class Top10FileFormats(RankingPanel):
    """
    Ranking formatów o największej liczbie plików
    """

    model = Resource
    x_axis_attr_name = "format"
    y_axis_attr_name = "resource_count"

    def init_labels(self):
        super().init_labels()
        self.x_axis_label = _("File format")
        self.y_axis_label = _("Number of data")

    def has_perm(self):
        perms = (self.user.is_authenticated,)

        return any(perms)

    def get_queryset(self):
        qs = super().get_queryset().filter(format__isnull=False)
        return qs.values("format").annotate(resource_count=Count("pk")).order_by("-resource_count")


class MostUsedCategories(RankingPanel):
    """
    Najczęściej używane kategorie
    """

    model = Category
    x_axis_attr_name = None
    y_axis_attr_name = "dataset__count"

    def init_labels(self):
        super().init_labels()
        self.x_axis_label = _("Category name")
        self.y_axis_label = _("Number of datasets")
        self.x_axis_attr_name = f"title_{self.lang}"

    def has_perm(self):
        perms = (self.user.is_authenticated,)

        return any(perms)

    def get_queryset(self):
        qs = super().get_queryset().exclude(code="")
        return (
            qs.values(self.x_axis_attr_name)
            .annotate(
                dataset__count=Count(
                    "dataset",
                    filter=Q(
                        dataset__is_removed=False,
                        dataset__is_permanently_removed=False,
                        dataset__status="published",
                    ),
                ),
            )
            .order_by("-dataset__count")
        )


class MostUsedTags(RankingPanel):
    """
    Najczęściej używane słowa kluczowe
    """

    model = Tag
    x_axis_attr_name = "name"
    y_axis_attr_name = "overall_tags"

    def init_labels(self):
        super().init_labels()
        self.x_axis_label = _("Tags")
        self.y_axis_label = _("Number of uses")

    def has_perm(self):
        perms = (self.user.is_authenticated,)

        return any(perms)

    def get_queryset(self):
        qs = super().get_queryset()
        base_sub_qs = qs.filter(pk=OuterRef("pk")).values("name")
        dataset_subquery = base_sub_qs.annotate(
            dataset_tags_count=Count(
                "dataset",
                filter=Q(
                    dataset__is_removed=False,
                    dataset__is_permanently_removed=False,
                    dataset__status="published",
                ),
                distinct=True,
            )
        ).values("dataset_tags_count")
        showcases_subquery = base_sub_qs.annotate(
            showcase_tags_count=Count(
                "showcase",
                filter=Q(
                    showcase__is_removed=False,
                    showcase__is_permanently_removed=False,
                    showcase__status="published",
                ),
                distinct=True,
            )
        ).values("showcase_tags_count")
        return (
            qs.values("name")
            .annotate(
                dataset_tags=Subquery(dataset_subquery, output_field=IntegerField()),
                showcase_tags=Subquery(showcases_subquery, output_field=IntegerField()),
            )
            .annotate(overall_tags=F("dataset_tags") + F("showcase_tags"))
            .order_by("-overall_tags")
        )


class MostSearchedQueries(RankingPanel):
    """
    Najczęściej wpisywane frazy w wyszukiwarce
    """

    model = SearchHistory
    x_axis_attr_name = "query_sentence"
    y_axis_attr_name = "search_count"

    def init_labels(self):
        super().init_labels()
        self.x_axis_label = _("Searched keyword")
        self.y_axis_label = _("Number of searches")

    def has_perm(self):
        perms = (self.user.is_authenticated,)

        return any(perms)

    def get_queryset(self):
        qs = SearchHistory.objects.all()
        return qs.values("query_sentence").annotate(search_count=Count("query_sentence")).order_by("-search_count")


class Top10LastMonthOrganizationNewDatasets(RankingPanel):
    """
    Ranking instytucji o największej liczbie nowych zbiorów danych w
     ostatnim pełnym miesiącu w ujęciu bezwględnym i procentowym
    """

    widgets_cls = {
        "presentation_type": PresentationTypeParamWidget,
        "viztypes": VizTypeParamWidget,
    }

    model = Dataset
    x_axis_attr_name = "organization__title"
    y_axis_attr_name = "dataset_count"
    variable_widget = "viztypes"

    def init_labels(self):
        super().init_labels()
        self.x_axis_label = "Instytucja"
        self.y_axis_label = "Liczba nowych zbiorów danych"
        self.p_map = {
            "absolute": "Bezwzględna liczba nowych zbiorów danych",
            "percentage": "Procent nowych zbiorów danych",
        }

    @property
    def value_dim_label(self):
        return self.p_map[self.presentation_type]

    def get_queryset(self):
        last_month_start = date.today() - relativedelta.relativedelta(months=1)
        qs = super().get_queryset().filter(created__date__gte=last_month_start)
        subquery = self.model.objects.filter(
            status="published",
            is_removed=False,
            is_permanently_removed=False,
        ).filter(created__date__lt=last_month_start)
        viz_types_dict = {
            "ct_table": Resource.objects.filter(dataset=OuterRef("pk"), has_table=True),
            "ct_chart": Resource.objects.filter(dataset=OuterRef("pk"), has_chart=True),
            "ct_map": Resource.objects.filter(dataset=OuterRef("pk"), has_map=True),
            "ct_none": Resource.objects.filter(dataset=OuterRef("pk"), has_map=False, has_chart=False, has_table=False),
        }
        if self.viztypes:
            selected_types = {v_type[0]: Exists(viz_types_dict[v_type[0]]) for v_type in self.viztypes}
        else:
            selected_types = {}
        qs = qs.annotate(**selected_types)
        subquery = (
            subquery.annotate(**selected_types)
            .filter(organization_id=OuterRef("organization_id"))
            .order_by()
            .values("organization_id")
        )
        count_filter = None
        single_type_counts = {}
        percentage_annotations = {}
        for selected_type in selected_types.keys():
            type_query = Q(**{selected_type: True})
            type_name = selected_type.split("_")[1]
            if not count_filter:
                count_filter = type_query
            else:
                count_filter |= type_query
            single_type_counts[f"{type_name}_count"] = Count("pk", filter=type_query)
            if self.presentation_type == "percentage":
                sub_annotate_label = f"sub_{type_name}_count"
                sub_annotate = {sub_annotate_label: Count("pk", filter=type_query)}
                single_type_counts[f"previous_{type_name}_count"] = Coalesce(
                    Subquery(
                        subquery.annotate(**sub_annotate).values(sub_annotate_label),
                        output_field=IntegerField(),
                    ),
                    0,
                )
                when_condition = {f"previous_{type_name}_count": 0, "then": 0}
                percentage_annotations[f"{type_name}_percentage"] = Case(
                    When(**when_condition),
                    default=Cast(F(f"{type_name}_count"), FloatField()) / Cast(F(f"previous_{type_name}_count"), FloatField()),
                )
        overall_count_expr = Count("pk", filter=count_filter, distinct=True) if count_filter else Count("pk")
        all_annotations = {"dataset_count": overall_count_expr}
        all_annotations.update(single_type_counts)
        values_list = list(single_type_counts.keys())
        if self.presentation_type == "percentage":
            all_annotations.update(
                {
                    "previous_dataset_count": Coalesce(
                        Subquery(
                            subquery.annotate(sub_datasets_count=overall_count_expr).values("sub_datasets_count"),
                            output_field=IntegerField(),
                        ),
                        0,
                    )
                }
            )
            values_list.append("previous_dataset_count")
        qs = qs.values("organization_id").annotate(**all_annotations)
        if self.presentation_type == "percentage":
            percentage_annotations["dataset_percentage"] = Case(
                When(previous_dataset_count=0, then=0),
                default=Cast(F("dataset_count"), FloatField()) / Cast(F("previous_dataset_count"), FloatField()),
            )
            qs = qs.annotate(**percentage_annotations)
            order_field = "-dataset_percentage"
            values_list.extend(list(percentage_annotations.keys()))
        else:
            order_field = "-dataset_count"
        return qs.values("dataset_count", "organization__title", *values_list).order_by(order_field)

    def get_dataframe(self):
        results = self.get_results()
        data = {}
        pres_types = getattr(self, "presentation_type") or "absolute"
        viztypes = self.viztypes or []
        selectedVizTypes = list(filter(lambda elem: elem[1] in viztypes, self.param.viztypes.names.items()))
        for _i, inst in enumerate(results):
            idx = data.setdefault(self.index_label, [])
            idx.append(_i + 1)
            n = data.setdefault(self.x_axis_label, [])
            n.append(inst[self.x_axis_attr_name])
            if viztypes:
                for key, val in selectedVizTypes:
                    m = data.setdefault(key, [])
                    count_key = val[0].split("_")[1]
                    num = inst.get(f"{count_key}_count", 0)
                    if self.presentation_type == "percentage":
                        num = inst.get(f"{count_key}_percentage", 0)
                        num = round(num, 2) * 100
                    m.append(num)
            else:
                m = data.setdefault(self.p_map[pres_types], [])
                amount = inst[self.y_axis_attr_name]
                if self.presentation_type == "percentage":
                    amount = inst["dataset_percentage"]
                    amount = round(amount, 2) * 100
                m.append(amount)
        if not data:
            data[self.index_label] = [1]
            data[self.x_axis_label] = ["Brak danych"]
            data[self.y_axis_label] = [0]
            data[self.p_map[pres_types]] = [0]

        df = pd.DataFrame(data=data)
        df.set_index(_("Entry"), inplace=True)
        return df

    def chart(self):
        chart = self.cached_df.plot.bar(**self.get_bar_kwargs())
        chart.opts(
            xlabel="",
            axiswise=True,
        )
        return chart


class CountChartByTimePeriod(ChartPanel):
    widgets_cls = {"timeperiod": TimePeriodParamWidget}
    y_axis_attr_name = "count_sum"
    x_axis_attr_name = "period"
    show_table_index = False

    def init_labels(self):
        self.x_axis_label = _("Period")

    def get_queryset(self):
        qs = self.model.objects.filter(
            resource__dataset__status="published",
            resource__dataset__is_removed=False,
            resource__dataset__is_permanently_removed=False,
        )
        qs = (
            qs.annotate(period=Trunc("timestamp", kind=self.timeperiod))
            .values("period")
            .annotate(count_sum=Sum("count"))
            .values("period", "count_sum")
            .order_by("period")
        )
        return qs

    def get_dataframe(self):
        data = {_("Entry"): [], _("Period"): [], self.y_axis_label: []}
        qs = self.get_results()
        try:
            periods = prepare_time_periods(qs[0]["period"], qs[-1]["period"], self.timeperiod)
            _data = OrderedDict()
            for i, itm in enumerate(periods):
                val = {self.y_axis_label: 0}
                val[_("Entry")] = i
                _data[itm] = val
            for item in qs:
                period = format_time_period(item["period"], self.timeperiod)
                _data[period][self.y_axis_label] = item["count_sum"]
            for period, period_details in _data.items():
                data[_("Entry")].append(period_details[_("Entry")])
                data[_("Period")].append(period)
                data[self.y_axis_label].append(period_details[self.y_axis_label])
        except IndexError:
            data[_("Entry")].append(0)
            data[_("Period")].append(_("None"))
            data[self.y_axis_label].append(0)
        df = pd.DataFrame(data=data)
        df.set_index(_("Entry"), inplace=True)
        return df

    def chart(self):
        chart = self.cached_df.plot.bar(legend="bottom", x=_("Period"), **self.get_chart_kwargs())
        chart.opts(xlabel="", axiswise=True, xrotation=90)
        return chart


class DatasetViewsCountByTimePeriod(CountChartByTimePeriod):
    def has_perm(self):
        perms = (self.user.is_authenticated,)

        return any(perms)

    model = ResourceViewCounter

    def init_labels(self):
        super().init_labels()
        self.y_axis_label = _("Views")


class DatasetDownloadsCountByTimePeriod(CountChartByTimePeriod):
    model = ResourceDownloadCounter

    def init_labels(self):
        super().init_labels()
        self.y_axis_label = _("Downloads")

    def has_perm(self):
        perms = (self.user.is_authenticated,)

        return any(perms)


class OrganizationGroupCountByTimePeriod(UserFilterMixin, CombinedChartMixin, CountChartByTimePeriod):
    queryset_widgets = {
        "organizations": {
            "widget_cls": UserGroupProvidersParamsWidget,
            "name": "Instytucje",
            "variable_label": "Instytucja",
        }
    }
    variable_widget = "organizations"

    def has_perm(self):
        perms = (self.user.agent,)

        return any(perms)

    def get_queryset_widget_kwargs(self):
        user_q = self.get_user_query("agents__pk")
        return {"organizations": {"query_params": user_q}}

    def get_queryset(self):
        if self.organizations:
            selected_organizations = [org[0] for org in self.organizations]
        else:
            selected_organizations = []
        group_values = ["period"]
        if selected_organizations:
            counter_query = Q(resource__dataset__organization_id__in=selected_organizations)
            group_values.extend(
                [
                    "resource__dataset__organization__title",
                    "resource__dataset__organization__pk",
                ]
            )
        else:
            counter_query = self.get_user_query("resource__dataset__organization__agents__pk")
        qs = self.model.objects.filter(
            counter_query,
            resource__dataset__status="published",
            resource__dataset__is_removed=False,
            resource__dataset__is_permanently_removed=False,
        )
        qs = (
            qs.annotate(period=Trunc("timestamp", kind=self.timeperiod))
            .values(*group_values)
            .annotate(count_sum=Sum("count"))
            .values("count_sum", *group_values)
            .order_by("period")
        )
        return qs

    def get_dataframe(self):
        if self.organizations:
            data = {
                _("Entry"): [],
                _("Period"): [],
            }
            organizations_dict = {org[0]: [] for org in self.organizations}
            data.update(organizations_dict)
            qs = self.get_results()
            mapping_details = Organization.objects.filter(pk__in=list(organizations_dict.keys())).values("pk", "title")
            column_name_mapping = {org["pk"]: org["title"] for org in mapping_details}
            try:
                periods = prepare_time_periods(qs[0]["period"], qs[-1]["period"], self.timeperiod)
                _data = OrderedDict()
                for i, itm in enumerate(periods):
                    val = {org[0]: 0 for org in self.organizations}
                    val[_("Entry")] = i
                    _data[itm] = val
                for item in qs:
                    period = format_time_period(item["period"], self.timeperiod)
                    _data[period][item["resource__dataset__organization__pk"]] = item["count_sum"]
                for period, period_details in _data.items():
                    data[_("Entry")].append(period_details[_("Entry")])
                    data[_("Period")].append(period)
                    for org in self.organizations:
                        data[org[0]].append(period_details[org[0]])
            except IndexError:
                data[_("Entry")].append(0)
                data[_("Period")].append(_("None"))
                for org in self.organizations:
                    data[org[0]].append(0)
            df = pd.DataFrame(data=data)
            df.set_index(_("Entry"), inplace=True)
            df.rename(columns=column_name_mapping, inplace=True)
            return df
        else:
            return super().get_dataframe()

    def chart(self):
        return self.get_combined_chart(self.cached_df)


class OrganizationGroupViewsCountByTimePeriod(OrganizationGroupCountByTimePeriod):
    model = ResourceViewCounter

    def init_labels(self):
        self.y_axis_label = "Liczba wyświetleń"

    @property
    def value_dim_label(self):
        return self.y_axis_label


class OrganizationGroupDownloadsCountByTimePeriod(OrganizationGroupCountByTimePeriod):
    model = ResourceDownloadCounter

    def init_labels(self):
        self.y_axis_label = "Liczba pobrań"

    @property
    def value_dim_label(self):
        return self.y_axis_label


class OrganizationGroupDatasetObservationByTimePeriod(UserOrganizationGroupMixin, CombinedChartMixin, ChartPanel):
    show_table_index = False
    widgets_cls = {"timeperiod": TimePeriodParamWidget}

    variable_widget = "organizations"

    def init_labels(self):
        self.y_axis_label = "Liczba obserwacji"

    @property
    def value_dim_label(self):
        return self.y_axis_label

    def has_perm(self):
        perms = (self.user.agent,)

        return any(perms)

    def get_queryset(self):
        grouping_vals = ["period"]
        if self.organizations:
            orgs_ids = [org[0] for org in self.organizations]
            dataset_q = Q(organization_id__in=orgs_ids)
            grouping_vals.append("sub_org_id")
        else:
            dataset_q = self.get_user_query("organization__agents__pk")
        ds = Dataset.objects.filter(
            dataset_q,
            pk=Cast(OuterRef("watcher__object_ident"), IntegerField()),
        ).values("organization_id")
        qs = (
            Subscription.objects.filter(watcher__object_name="datasets.Dataset")
            .annotate(period=Trunc("created", kind=self.timeperiod))
            .values("period")
            .annotate(sub_org_id=Subquery(ds, output_field=CharField()))
            .filter(sub_org_id__isnull=False)
            .values(*grouping_vals)
        )
        if self.organizations:
            qs = qs.annotate(subs_count=Count("sub_org_id"))
        else:
            qs = qs.annotate(subs_count=Count("pk"))
        return qs.values(*grouping_vals, "subs_count").order_by("period")

    def get_dataframe(self):
        data = {
            _("Entry"): [],
            _("Period"): [],
        }
        qs = self.get_results()
        if self.organizations:
            column_name_mapping = self.get_org_specific_data(data, qs)
        else:
            data[self.y_axis_label] = []
            try:
                periods = prepare_time_periods(qs[0]["period"], qs[-1]["period"], self.timeperiod)
                _data = OrderedDict()
                for i, itm in enumerate(periods):
                    val = {self.y_axis_label: 0, _("Entry"): i}
                    _data[itm] = val
                for item in qs:
                    period = format_time_period(item["period"], self.timeperiod)
                    _data[period][self.y_axis_label] = item["subs_count"]
                for period, period_details in _data.items():
                    data[_("Entry")].append(period_details[_("Entry")])
                    data[_("Period")].append(period)
                    data[self.y_axis_label].append(period_details[self.y_axis_label])
            except IndexError:
                data[_("Entry")].append(0)
                data[_("Period")].append(_("None"))
                data[self.y_axis_label].append(0)

        df = pd.DataFrame(data=data)
        df.set_index(_("Entry"), inplace=True)
        try:
            df.rename(columns=column_name_mapping, inplace=True)
        except UnboundLocalError:
            pass
        return df

    def get_org_specific_data(self, data, qs):
        org_dict = {org[0]: [] for org in self.organizations}
        data.update(org_dict)
        org_ids = list(org_dict.keys())
        mapping_details = Organization.objects.filter(pk__in=org_ids).values("pk", "title")
        column_name_mapping = {org["pk"]: org["title"] for org in mapping_details}
        try:
            periods = prepare_time_periods(qs[0]["period"], qs[-1]["period"], self.timeperiod)
            _data = OrderedDict()
            for i, itm in enumerate(periods):
                val = {org[0]: 0 for org in self.organizations}
                val[_("Entry")] = i
                _data[itm] = val
            for item in qs:
                period = format_time_period(item["period"], self.timeperiod)
                _data[period][item["sub_org_id"]] = item["subs_count"]
            for period, period_details in _data.items():
                data[_("Entry")].append(period_details[_("Entry")])
                data[_("Period")].append(period)
                for org in self.organizations:
                    data[org[0]].append(period_details[org[0]])
        except IndexError:
            data[_("Entry")].append(0)
            data[_("Period")].append(_("None"))
            for org in self.organizations:
                data[org[0]].append(0)
        return column_name_mapping

    def chart(self):
        return self.get_combined_chart(self.cached_df)


class Top10ObservedDatasets(RankingPanel):
    """
    Ranking obserwacji zbiorów danych
    """

    model = Dataset
    x_axis_attr_name = "dataset_title"
    y_axis_attr_name = "subs_count"

    def init_labels(self):
        super().init_labels()
        self.y_axis_label = "Liczba obserwacji"
        self.x_axis_label = "Zbiór danych"

    def get_queryset(self):
        ds = super().get_queryset()
        ds = ds.filter(pk=Cast(OuterRef("watcher__object_ident"), IntegerField())).values("title")
        qs = (
            Subscription.objects.filter(watcher__object_name="datasets.Dataset")
            .annotate(dataset_title=Subquery(ds, output_field=CharField()))
            .values("dataset_title", "watcher__object_ident")
            .annotate(subs_count=Count("watcher__object_ident"))
            .values("dataset_title", "subs_count")
        )
        return qs.order_by("-subs_count")


class DatasetsCountByTimePeriodForGroup(DataCountByTimePeriodForGroup):
    """
    Liczba zbiorów danych dla swojej grupy instytucji w podziale na miesiące/kwartały/lata
    """

    widgets_cls = {
        "timeperiod": TimePeriodParamWidget,
        "viztypes": VizTypeParamWidget,
    }
    select_widget = "viztypes"
    variable_widget = "viztypes"
    case_subqueries = {
        "ct_table": "SUM(COUNT(CASE WHEN EXISTS (SELECT 1 FROM resource r WHERE d.id = r.dataset_id AND"
        " r.is_removed = FALSE AND r.status = 'published' AND r.has_table = TRUE) THEN d.id END))"
        " OVER(PARTITION BY o.title ORDER BY "
        "DATE_TRUNC('MONTH', d.created AT TIME ZONE 'Europe/Warsaw')) table_count",
        "ct_map": "SUM(COUNT(CASE WHEN EXISTS (SELECT 1 FROM resource r WHERE d.id = r.dataset_id AND"
        " r.is_removed = FALSE AND r.status = 'published' AND r.has_map = TRUE) THEN d.id END))"
        " OVER(PARTITION BY o.title ORDER BY "
        "DATE_TRUNC('MONTH', d.created AT TIME ZONE 'Europe/Warsaw'))   map_count",
        "ct_chart": "SUM(COUNT(CASE WHEN EXISTS (SELECT 1 FROM resource r WHERE d.id = r.dataset_id AND"
        " r.is_removed = FALSE AND r.status = 'published' AND r.has_chart = TRUE) THEN d.id END))"
        " OVER(PARTITION BY o.title ORDER BY "
        "DATE_TRUNC('MONTH', d.created AT TIME ZONE 'Europe/Warsaw')) chart_count",
        "ct_none": "SUM(COUNT(CASE WHEN EXISTS (SELECT 1 FROM resource r WHERE d.id = r.dataset_id AND"
        " r.is_removed = FALSE AND r.status = 'published' AND r.has_table = FALSE AND"
        " r.has_map = FALSE AND r.has_chart = FALSE) THEN d.id END))"
        " OVER(PARTITION BY o.title ORDER BY "
        "DATE_TRUNC('MONTH', d.created AT TIME ZONE 'Europe/Warsaw'))  none_count",
    }
    default_subquery = (
        "SUM(COUNT(d.id)) OVER(PARTITION BY o.title ORDER BY "
        "DATE_TRUNC('MONTH', d.created AT TIME ZONE 'Europe/Warsaw')) all_count"
    )

    def get_main_sql(self, filter_query, select_query):
        sql = (
            """
            SELECT o.title organization,
                DATE_TRUNC('MONTH', d.created AT TIME ZONE 'Europe/Warsaw') period,
                """
            + select_query
            + """
            FROM organization o
                JOIN user_agent_organizations a ON o.id = a.organization_id
                JOIN dataset d ON o.id = d.organization_id
            WHERE o.is_removed = FALSE
                AND d.is_removed = FALSE
                AND d.status = 'published'
                AND """
            + filter_query
            + """
            GROUP BY o.title, DATE_TRUNC('MONTH', d.created AT TIME ZONE 'Europe/Warsaw')
            ORDER BY period, organization;
        """
        )
        return sql

    def get_count_key_label(self, val):
        return val[0].split("_")[1]


class NewDatasetsByTimePeriodForGroup(NewDataByTimePeriodForGroup):
    """
    Liczba nowych zbiorów danych dla swojej grupy instytucji w podziale na miesiące/kwartały/lata
    """

    widgets_cls = {
        "timeperiod": TimePeriodParamWidget,
        "viztypes": VizTypeParamWidget,
        "presentation_type": PresentationTypeParamWidget,
    }
    select_widget = "viztypes"
    variable_widget = "viztypes"

    @property
    def value_dim_label(self):
        return self.p_map[self.presentation_type]

    case_subqueries = {
        "ct_table": "COUNT(CASE WHEN EXISTS (SELECT 1 FROM resource r WHERE d.id = r.dataset_id AND"
        " r.is_removed = FALSE AND r.status = 'published' AND r.has_table = TRUE) THEN d.id END)"
        " table_count",
        "ct_map": "COUNT(CASE WHEN EXISTS (SELECT 1 FROM resource r WHERE d.id = r.dataset_id AND"
        " r.is_removed = FALSE AND r.status = 'published' AND r.has_map = TRUE) THEN d.id END)"
        " map_count",
        "ct_chart": "COUNT(CASE WHEN EXISTS (SELECT 1 FROM resource r WHERE d.id = r.dataset_id AND"
        " r.is_removed = FALSE AND r.status = 'published' AND r.has_chart = TRUE) THEN d.id END)"
        " chart_count",
        "ct_none": "COUNT(CASE WHEN EXISTS (SELECT 1 FROM resource r WHERE d.id = r.dataset_id AND"
        " r.is_removed = FALSE AND r.status = 'published' AND r.has_table = FALSE AND"
        " r.has_map = FALSE AND r.has_chart = FALSE) THEN d.id END)  none_count",
    }
    default_subquery = "COUNT(d.id) all_count"

    def get_main_sql(self, filter_query, select_query):
        sql = (
            """
                SELECT o.title organization,
                    DATE_TRUNC('MONTH', d.created AT TIME ZONE 'Europe/Warsaw') period,
                     """
            + select_query
            + """
                FROM organization o
                    JOIN user_agent_organizations a ON o.id = a.organization_id
                    JOIN dataset d ON o.id = d.organization_id
                WHERE o.is_removed = FALSE
                    AND d.is_removed = FALSE
                    AND d.status = 'published'
                    AND """
            + filter_query
            + """
                GROUP BY o.title, DATE_TRUNC('MONTH', d.created AT TIME ZONE 'Europe/Warsaw')
                ORDER BY period, organization;
            """
        )
        return sql

    def get_count_key_label(self, val):
        return val[0].split("_")[1]


class NewResourcesForInstitutionsGroupByTimePeriod(NewDataByTimePeriodForGroup):
    """
    Liczba nowych zasobów dla swojej grupy instytucji w podziale na miesiące/kwartały/lata
    """

    widgets_cls = {
        "timeperiod": TimePeriodParamWidget,
        "restypes": ResourceTypeParamWidget,
        "presentation_type": PresentationTypeParamWidget,
    }
    select_widget = "restypes"
    variable_widget = "restypes"

    @property
    def value_dim_label(self):
        return self.p_map[self.presentation_type]

    case_subqueries = {
        "file": "COUNT(CASE WHEN r.TYPE = 'file' THEN r.id END) file_count",
        "website": "COUNT(CASE WHEN r.TYPE = 'website' THEN r.id END) website_count",
        "api": "COUNT(CASE WHEN r.TYPE = 'api' THEN r.id END) api_count",
    }
    default_subquery = "COUNT(1) all_count"

    def get_main_sql(self, filter_query, select_query):
        sql = (
            """
            SELECT o.title organization,
                DATE_TRUNC('MONTH', r.created AT TIME ZONE 'Europe/Warsaw') period,
                """
            + select_query
            + """
            FROM organization o
                JOIN user_agent_organizations a ON o.id = a.organization_id
                JOIN dataset d ON o.id = d.organization_id
                JOIN resource r ON d.id = r.dataset_id
            WHERE o.is_removed = FALSE
                AND d.is_removed = FALSE
                AND d.status = 'published'
                AND r.is_removed = FALSE
                AND r.status = 'published'
                AND """
            + filter_query
            + """
            GROUP BY o.title, DATE_TRUNC('MONTH', r.created AT TIME ZONE 'Europe/Warsaw')
            ORDER BY period, organization;
        """
        )
        return sql

    def get_count_key_label(self, val):
        return val[0]


class ResourcesForInstitutionsGroupByTimePeriod(DataCountByTimePeriodForGroup):
    """
    Liczba zasobów dla swojej grupy instytucji w podziale na miesiące/kwartały/lata
    """

    widgets_cls = {
        "timeperiod": TimePeriodParamWidget,
        "restypes": ResourceTypeParamWidget,
    }
    select_widget = "restypes"
    variable_widget = "restypes"

    case_subqueries = {
        "file": "SUM(COUNT(CASE WHEN r.TYPE = 'file' THEN r.id END)) OVER(PARTITION BY o.title ORDER BY"
        " DATE_TRUNC('MONTH', r.created AT TIME ZONE 'Europe/Warsaw')) file_count",
        "website": "SUM(COUNT(CASE WHEN r.TYPE = 'website' THEN r.id END))"
        " OVER(PARTITION BY o.title ORDER BY DATE_TRUNC('MONTH', r.created AT TIME ZONE 'Europe/Warsaw'))"
        " website_count",
        "api": "SUM(COUNT(CASE WHEN r.TYPE = 'api' THEN r.id END)) OVER(PARTITION BY o.title ORDER BY "
        "DATE_TRUNC('MONTH', r.created AT TIME ZONE 'Europe/Warsaw')) api_count",
    }
    default_subquery = (
        "SUM(COUNT(r.id)) OVER(PARTITION BY o.title ORDER BY "
        "DATE_TRUNC('MONTH', r.created AT TIME ZONE 'Europe/Warsaw')) all_count"
    )

    def get_main_sql(self, filter_query, select_query):
        sql = (
            """
            SELECT o.title organization,
                DATE_TRUNC('MONTH', r.created AT TIME ZONE 'Europe/Warsaw') period,
                """
            + select_query
            + """
            FROM organization o
                JOIN user_agent_organizations a ON o.id = a.organization_id
                JOIN dataset d ON o.id = d.organization_id
                JOIN resource r ON d.id = r.dataset_id
            WHERE o.is_removed = FALSE
                AND d.is_removed = FALSE
                AND d.status = 'published'
                AND r.is_removed = FALSE
                AND r.status = 'published'
                AND """
            + filter_query
            + """
            GROUP BY o.title, DATE_TRUNC('MONTH', r.created AT TIME ZONE 'Europe/Warsaw')
            ORDER BY period, organization;
        """
        )
        return sql

    def get_count_key_label(self, val):
        return val[0]


def app(doc):
    app_start = time()
    language = doc.session_context.request.cookies.get("currentLang", settings.LANGUAGE_CODE)
    if language not in settings.MODELTRANS_AVAILABLE_LANGUAGES:
        language = settings.LANGUAGE_CODE
    locale_code = settings.LANG_TO_LOCALE.get(language, settings.LANGUAGE_CODE)
    set_locale(locale_code)
    activate(language)
    user = doc.session_context.request._request.user
    if user.is_authenticated:
        widget_kwargs = {}
        charts_kwargs = {
            "user": user,
            "doc": doc,
            "fav_charts_widget": pn.widgets.TextInput(value=json.dumps(user.fav_charts)),
            "lang": language,
        }
        user_agent = doc.session_context.request.headers.get("user-agent")
        if user_agent:
            charts_kwargs["agent_type"] = parse(user_agent)
        chart_init_start = time()
        charts = [
            Top10ProvidersByResourcesCount(name="Ranking instytucji o największej liczbie danych", **charts_kwargs),
            ResourcesCountByTimePeriod(name="Liczba danych", **charts_kwargs),
            NewResourcesCountByTimePeriod(name="Liczba nowych danych", **charts_kwargs),
            Top10ProvidersByDatasetsCount(
                name="Ranking instytucji o największej liczbie zbiorów danych",
                **charts_kwargs,
            ),
            DatasetsCountByTimePeriod(name=_("Number of datasets"), **charts_kwargs),
            NewDatasetsCountByTimePeriod(name=_("Number of datasets added"), **charts_kwargs),
            DatasetsCountByTimePeriodForGroup(name="Liczba zbiorów danych dla grupy instytucji", **charts_kwargs),
            NewDatasetsByTimePeriodForGroup(
                name="Liczba nowych zbiorów danych dla grupy instytucji",
                **charts_kwargs,
            ),
            NewResourcesForInstitutionsGroupByTimePeriod(name="Liczba nowych danych dla grupy instytucji", **charts_kwargs),
            ResourcesForInstitutionsGroupByTimePeriod(name="Liczba danych dla grupy instytucji", **charts_kwargs),
            Top10MostDownloadedDatasets(name=_("Most downloaded datasets"), **charts_kwargs),
            Top10MostViewedDatasets(name=_("Most viewed datasets"), **charts_kwargs),
            Top10OrganizationsMostDownloadedDatasets(name="Ranking instytucji o największej liczbie pobrań", **charts_kwargs),
            Top10MostPopularOrganizations(name="Ranking instytucji o największej popularności", **charts_kwargs),
            TopResourceCountOrgfromGroup(
                name="Ranking instytucji o największej liczbie danych dla grupy instytucji",
                **charts_kwargs,
            ),
            Top10MostDownloadedResources(name="Ranking danych o największej liczbie pobrań", **charts_kwargs),
            Top10MostPopularResources(name="Ranking danych o największej popularności", **charts_kwargs),
            ResourceOpennessReportChart(name=_("Datasets openess rating"), **charts_kwargs),
            Top10FileFormats(name=_("Top file formats"), **charts_kwargs),
            MostUsedCategories(name=_("Top themes"), **charts_kwargs),
            MostUsedTags(name=_("Top tags"), **charts_kwargs),
            MostSearchedQueries(name=_("Top keywords"), **charts_kwargs),
            Top10LastMonthOrganizationNewDatasets(
                name="Ranking instytucji o największej liczbie nowych zbiorów danych w ostatnim miesiącu ",
                **charts_kwargs,
            ),
            OrganizationGroupDatasetObservationByTimePeriod(
                name="Liczba obserwacji zbiorów danych dla grupy instytucji",
                **charts_kwargs,
            ),
            Top10ObservedDatasets(name="Ranking obserwacji zbiorów danych", **charts_kwargs),
            DatasetViewsCountByTimePeriod(name=_("Views of datasets"), **charts_kwargs),
            DatasetDownloadsCountByTimePeriod(name=_("Downloads of datasets"), **charts_kwargs),
            OrganizationGroupViewsCountByTimePeriod(name="Liczba wyświetleń danych dla grupy instytucji", **charts_kwargs),
            OrganizationGroupDownloadsCountByTimePeriod(name="Liczba pobrań danych dla grupy instytucji", **charts_kwargs),
        ]
        chart_init_end = time()
        charts_init_delta = chart_init_end - chart_init_start
        profile_log.debug("Charts initialization: %.4f" % charts_init_delta)
        permitted_charts = [chart for chart in charts if chart.has_perm()]
        widgets_start = time()
        event_widgets = register_event_widgets(permitted_charts, widget_kwargs)
        widgets_end = time()
        widgets_total = widgets_end - widgets_start
        profile_log.debug("Widgets Register: %.4f" % widgets_total)
        chart_panel_start = time()
        charts_panels = [chart.panel() for chart in permitted_charts]
        chart_panel_end = time()
        chart_panel_total = chart_panel_end - chart_panel_start
        profile_log.debug("All charts panels init: %.4f" % chart_panel_total)
        all_models = event_widgets + charts_panels
        dashboard = pn.Column(
            *all_models,
            sizing_mode="stretch_both",
            width_policy="max",
            height_policy="max",
        )
        pre_server_doc_app_end = time()
        pre_server_doc_total_app_time = pre_server_doc_app_end - app_start
        profile_log.debug("APP FUNC TIME BEFORE SERVER DOC: %.4f" % pre_server_doc_total_app_time)
        server_doc_start = time()
        dashboard.server_doc(doc)
        server_doc_end = time()
        total_server_doc = server_doc_end - server_doc_start
        profile_log.debug("DASHBOARD SERVER DOC TIME: %.4f" % total_server_doc)
        app_end = time()
        total_app_time = app_end - app_start
        profile_log.debug("WHOLE APP FUNC TIME: %.4f" % total_app_time)
