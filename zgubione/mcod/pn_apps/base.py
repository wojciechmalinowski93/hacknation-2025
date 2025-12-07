import json
import logging
from collections import OrderedDict
from functools import partial
from io import BytesIO
from time import time

import holoviews as hv
import numpy as np
import pandas as pd
import panel as pn
import param
from bokeh.io.export import get_screenshot_as_png
from bokeh.models import BasicTicker, CompositeTicker, FuncTickFormatter
from django.db import connections
from django.utils.functional import cached_property
from django.utils.translation import gettext as _
from panel.io.state import state

from mcod.organizations.models import Organization
from mcod.pn_apps.bokeh.tools.base import (
    LocalizedHoverTool,
    LocalizedPanTool,
    LocalizedResetTool,
    LocalizedSaveTool,
    LocalizedWheelZoomTool,
)
from mcod.pn_apps.layout import ExtendedColumn
from mcod.pn_apps.mixins import CombinedChartMixin, UserOrganizationGroupMixin
from mcod.pn_apps.utils import (
    chart_thumb_path,
    format_time_period,
    prepare_time_periods,
    reformat_time_period,
)
from mcod.pn_apps.widgets import BootstrapTableTemplate, TabbedBootstrapTableTemplate

q_log = logging.getLogger("stats-queries")
profile_log = logging.getLogger("stats-profile")


class StatsPanel(param.Parameterized):
    table_template_cls = BootstrapTableTemplate
    widgets_cls = {}
    queryset_widgets = {}
    show_table_index = True
    show_initial_table = True
    generic_dim_names = {"Variable", "value"}

    def __init__(
        self,
        user,
        lang,
        agent_type=None,
        doc=None,
        fav_charts_widget=None,
        theme_name="",
        **params,
    ):
        self.user = user
        self.agent_type = agent_type
        self.lang = lang
        self.doc = doc
        self.fav_charts_widget = fav_charts_widget
        self._active_style = theme_name
        if self.show_initial_table:
            toggle_label = _("Hide table")
        else:
            toggle_label = _("View table")
        self.queryset_widgets_objs = {}
        self.toggle_widget = pn.widgets.Toggle(name=toggle_label, value=self.show_initial_table, max_width=30)
        self.fav_chart_1_widget = pn.widgets.Checkbox(
            name="1",
            width_policy="min",
            align="start",
            height_policy="min",
            css_classes=[
                "fav-checkbox",
            ],
        )
        self.fav_chart_2_widget = pn.widgets.Checkbox(
            name="2",
            width_policy="min",
            align="start",
            height_policy="min",
            css_classes=[
                "fav-checkbox",
            ],
        )

        if self.fav_charts_widget:
            self.fav_charts_widget.param.watch(self.on_fav_charts_changed, "value")

        super().__init__(**params)
        common_dependencies = []
        self.init_queryset_widgets(common_dependencies)
        self.widgets = {widget_name: widget() for widget_name, widget in self.widgets_cls.items()}
        for _name, _inst in self.widgets.items():
            self.param._add_parameter(_name, _inst.param)
            common_dependencies.append(_name)
        self.param._add_parameter("new_theme_name", param.String(default=self._active_style, precedence=-1))
        self.param._add_parameter("show_table", param.Boolean(default=self.show_initial_table, precedence=-1))
        self.col = None
        chart_dependencies = common_dependencies + ["new_theme_name"]
        table_dependencies = common_dependencies + ["show_table"]
        param.depends(self.render_chart, chart_dependencies, watch=False)
        self.toggle_widget.link(self, callbacks={"value": self.table_toggle_callback})
        self.fav_chart_1_widget.link(self, callbacks={"value": partial(self.fav_chart_callback, 1)})
        self.fav_chart_2_widget.link(self, callbacks={"value": partial(self.fav_chart_callback, 2)})

        code = {"value": "target.disabled = true;"}
        self.fav_chart_1_widget.jslink(self.fav_chart_2_widget, code=code)
        self.fav_chart_2_widget.jslink(self.fav_chart_1_widget, code=code)

        if self.fav_charts_widget:
            self._setup_fav_chart_widgets(self.fav_charts_widget.value)
        if common_dependencies:
            param.depends(self.table, table_dependencies, watch=False)

    def init_queryset_widgets(self, common_dependencies):
        for widget_label, widget_details in self.queryset_widgets.items():
            widget_kwargs = self.get_queryset_widget_kwargs()[widget_label]
            widget_kwargs.update({"name": widget_details["name"]})
            widget = widget_details["widget_cls"](**widget_kwargs)
            self.queryset_widgets_objs[widget_label] = widget
            self.param._add_parameter(widget_label, widget.param)
            common_dependencies.append(widget_label)

    def get_queryset_widget_kwargs(self):
        return {}

    def save_as_png(self, slot=1):
        filename = chart_thumb_path(self.user, slot)
        chart = self.chart()
        chart.opts(width=500, height=500, toolbar=None, backend="bokeh", clone=False)
        hv.save(
            chart,
            filename,
            post_render_hooks={"png": [self.assign_adaptive_ticker_post_render_hook]},
        )
        # TODO Hack!]
        if self.doc:
            self.doc.remove_root(self.doc.roots[-1])

    def on_fav_charts_changed(self, event):
        if event.type == "changed" and event.what == "value":
            self._setup_fav_chart_widgets(event.new)

    def _setup_fav_chart_widgets(self, data):
        ident = self.__class__.__name__
        data = json.loads(data)
        slot1 = data.get("slot-1", {})
        is_slot1_checked = bool(slot1 and slot1.get("ident") == ident)
        slot2 = data.get("slot-2", {})
        is_slot2_checked = bool(slot2 and slot2.get("ident") == ident)
        self.fav_chart_1_widget.value = is_slot1_checked
        self.fav_chart_2_widget.value = is_slot2_checked

        if not is_slot1_checked and is_slot2_checked:
            self.fav_chart_1_widget.disabled = True
        if is_slot1_checked and not is_slot2_checked:
            self.fav_chart_2_widget.disabled = True
        if not is_slot1_checked and not is_slot2_checked:
            self.fav_chart_1_widget.disabled = False
            self.fav_chart_2_widget.disabled = False

    @staticmethod
    def fav_chart_callback(slot, target, event):
        slot_name = f"slot-{slot}"
        ident = target.__class__.__name__
        # Get favs value from user field
        if event.type == "changed" and event.what == "value":
            fav_charts = target.user.fav_charts or {}
            chart_data = fav_charts.setdefault(slot_name, {})
            if chart_data.get("ident") != ident:
                if event.new:
                    chart_data = {"ident": ident, "name": target.name}
                else:
                    return
            else:
                if event.new:
                    return
                else:
                    chart_data = {}

            fav_charts[slot_name] = chart_data
            target.user.fav_charts = fav_charts
            target.user.save()
            target.save_as_png(slot=slot)
            target.fav_charts_widget.value = json.dumps(target.user.fav_charts)

    @staticmethod
    def table_toggle_callback(target, event):
        target.show_table = event.new
        if event.new:
            event.obj.name = _("Hide table")
        else:
            event.obj.name = _("View table")

    @property
    def qs(self):
        return self.get_queryset()

    @cached_property
    def cached_df(self):
        return self.post_process_dataframe()

    @property
    def variable_dim_label(self):
        try:
            dim_label = self.widgets[self.variable_widget].alt_title
        except KeyError:
            dim_label = self.queryset_widgets[self.variable_widget].get("variable_label", "Variable")
        return dim_label

    @property
    def value_dim_label(self):
        return _("Number")

    def render_chart(self):
        start = time()
        self.invalidate_cache()
        chart = self.chart()
        chart.opts(default_tools=[], hooks=[self.apply_post_hooks])
        end = time()
        total = end - start
        profile_log.debug("%s; render_chart ;%.4f" % (self.name, total))
        return chart

    def assign_adaptive_ticker(self, rendered_chart, desired_num_ticks=None):
        plot_factors = rendered_chart.x_range.factors
        if desired_num_ticks is None:
            desired_num_ticks = self.get_desired_num_ticks(plot_factors)
        if self.agent_type and self.agent_type.is_mobile and plot_factors and not plot_factors[0].isnumeric():
            sub_ticker_intervals = [0.5, 1.5, 2.5, 3.5]
            sub_tickers = [BasicTicker(max_interval=0.25, desired_num_ticks=desired_num_ticks)]
            for interval in sub_ticker_intervals:
                sub_tickers.append(
                    BasicTicker(
                        min_interval=interval,
                        max_interval=interval,
                        desired_num_ticks=desired_num_ticks,
                    )
                )
            ticker = CompositeTicker(tickers=sub_tickers)
        else:
            ticker = BasicTicker(min_interval=0.25, desired_num_ticks=desired_num_ticks)
        rendered_chart.xaxis[0].ticker = ticker
        label_overrides = {index - 0.5: dt for index, dt in enumerate(plot_factors, start=1)}
        label_indexes = list(label_overrides.keys())
        conditional_formatter_code = """
            if(label_indexes.indexOf(tick) >= 0){
                return label_dict[tick];
            }
            else{
                return ""
            }
            """
        rendered_chart.xaxis[0].formatter = FuncTickFormatter(
            code=conditional_formatter_code,
            args={"label_indexes": label_indexes, "label_dict": label_overrides},
        )

    def get_desired_num_ticks(self, plot_factors):
        if self.agent_type and self.agent_type.is_mobile:
            desired_num_ticks = self.get_factor_type_dependent_ticks(plot_factors)
        else:
            desired_num_ticks = 2 * len(plot_factors)
        return desired_num_ticks

    @staticmethod
    def get_factor_type_dependent_ticks(plot_factors):
        desired_num_ticks = len(plot_factors)
        if plot_factors and plot_factors[0].isnumeric():
            desired_num_ticks *= 2
        else:
            desired_num_ticks = desired_num_ticks
        return desired_num_ticks

    def assign_adaptive_ticker_post_render_hook(self, rendered_data, rendered_obj):
        plot_factors = rendered_obj.state.x_range.factors
        desired_num_ticks = self.get_factor_type_dependent_ticks(plot_factors)
        self.assign_adaptive_ticker(rendered_obj.state, desired_num_ticks)
        img = get_screenshot_as_png(rendered_obj.state, driver=state.webdriver)
        imgByteArr = BytesIO()
        img.save(imgByteArr, format="PNG")
        data = imgByteArr.getvalue()
        return data

    def add_toolbar(self, rendered_chart, chart):
        custom_hover = self.init_custom_tooltip(chart)
        rendered_chart.toolbar.logo = None
        rendered_chart.tools = []
        rendered_chart.add_tools(
            custom_hover,
            LocalizedPanTool(dimensions="width", localized_tool_name=_("Pan")),
            LocalizedWheelZoomTool(dimensions="width", localized_tool_name=_("Zoom")),
            LocalizedSaveTool(localized_tool_name=_("Save")),
            LocalizedResetTool(localized_tool_name=_("Reset")),
        )
        return rendered_chart

    def init_custom_tooltip(self, chart):
        dims_names = set([kdim.name for kdim in chart.kdims] + [vdim.name for vdim in chart.vdims])
        if not dims_names:
            dims_names = set([kdim.name for kdim in chart.ddims])
        non_generic_dims = dims_names.difference(self.generic_dim_names)
        existing_generic_dims = self.generic_dim_names.intersection(dims_names)
        tooltips = []
        for dim in non_generic_dims:
            tooltips.append((dim, f"@{{{hv.core.util.dimension_sanitizer(dim)}}}"))
        if existing_generic_dims:
            tooltips.extend(
                [
                    (self.variable_dim_label, "@Variable"),
                    (self.value_dim_label, "@value"),
                ]
            )
        return LocalizedHoverTool(tooltips=tooltips, localized_tool_name=_("Hover"))

    def chart(self):
        return None

    def table_template(self, df):
        return self.table_template_cls(df, self.name, show_table_index=self.show_table_index)

    def table(self):
        if self.show_table:
            start = time()
            df = self.cached_df.copy()
            if hasattr(self, "timeperiod") and self.timeperiod == "month":
                df[_("Period")] = df[_("Period")].apply(reformat_time_period)
            row = pn.Row(
                pn.pane.HTML(
                    self.table_template(df),
                    sizing_mode="stretch_width",
                    width_policy="max",
                ),
                sizing_mode="stretch_width",
                width_policy="max",
                height_policy="max",
            )
            end = time()
            total = end - start
            profile_log.debug("%s; table ;%.4f" % (self.name, total))
            return row
        else:
            return None

    def has_perm(self):
        return False

    def panel(self):
        start = time()
        if not self.has_perm():
            return None
        kwargs = {}
        widget_params = {name: item.widget for name, item in self.widgets.items()}
        widget_params.update({name: item.widget for name, item in self.queryset_widgets_objs.items()})
        if widget_params:
            kwargs["widgets"] = widget_params
        fav_chart_kwargs = {
            "width_policy": "min",
            "height_policy": "min",
            "align": "start",
            "css_classes": ["fav-container"],
        }
        if self.agent_type and self.agent_type.is_mobile:
            del fav_chart_kwargs["css_classes"]
        default_kwargs = {
            "sizing_mode": "stretch_both",
            "width_policy": "max",
            "height_policy": "max",
            "css_classes": ["stat-container"],
            "margin": (24, 0),
        }
        default_args = [
            pn.Row(
                _("**Add to dashboard:**"),
                self.fav_chart_1_widget,
                self.fav_chart_2_widget,
                **fav_chart_kwargs,
            ),
            pn.Column(
                pn.panel(
                    self.param,
                    show_name=False,
                    show_labels=False,
                    sizing_mode="stretch_both",
                    **kwargs,
                ),
                sizing_mode="stretch_width",
                width_policy="max",
                height_policy="max",
            ),
            pn.panel(
                ExtendedColumn(
                    self.render_chart,
                    sizing_mode="stretch_both",
                    width_policy="max",
                    height_policy="max",
                    aria_hidden=True,
                    css_classes=["canvas-container"],
                ),
            ),
            pn.Column(self.toggle_widget, margin=(12, 0, 0, 0)),
            self.table,
        ]
        default_kwargs.update(
            {
                "header": pn.pane.HTML(
                    f'<h2 class="heading heading--sm">{self.name}</>',
                    sizing_mode="stretch_width",
                    style={"text-align": "left", "margin-top": "18px"},
                ),
                "margin": (6, 0),
                "header_background": "#fff",
                "collapsed": True,
                "button_css_classes": ["stats-card-button"],
            }
        )
        col = pn.Card(*default_args, **default_kwargs)
        end = time()
        total = end - start
        profile_log.debug("%s; panel ;%.4f" % (self.name, total))
        return col

    def invalidate_cache(self):
        if self.new_theme_name == self._active_style:
            try:
                del self.cached_df
            except AttributeError:
                pass
        else:
            self._active_style = self.new_theme_name

    def get_queryset(self):
        if hasattr(self, "model"):
            return self.model.objects.filter(status="published")
        else:
            raise NotImplementedError('Class must implement "model" field')

    def get_dataframe(self):
        raise NotImplementedError

    def get_results(self):
        sql = str(self.qs.query)
        start = time()
        result = list(self.qs)
        total = time() - start
        q_log.debug("%s;%.4f;%s" % (self.name, total, sql))
        return result

    def post_process_dataframe(self):
        start = time()
        df = self.get_dataframe()
        end = time()
        total = end - start
        profile_log.debug("%s; get_dataframe; %.4f" % (self.name, total))
        data_columns = df.columns[1:]
        query = " | ".join([f"`{column_name}` > 0" for column_name in data_columns])
        try:
            if self.widgets.get("timeperiod"):
                df_index = df.query(query).index.min()
                df = df.iloc[df_index:]
            else:
                df_index = df.query(query).index.max()
                df = df.iloc[:df_index]
        except TypeError:
            pass
        return df

    def apply_post_hooks(self, plot, element):
        start = time()
        self.add_toolbar(plot.state, element)
        self.assign_adaptive_ticker(plot.state)
        end = time()
        total = end - start
        profile_log.debug("%s; apply_post_hooks;%.4f;" % (self.name, total))

    def get_chart_kwargs(self):
        kwargs = {
            "aspect": 1.5 if getattr(self.agent_type, "is_mobile", False) else 2,
            "responsive": True,
        }
        return kwargs


class RawSqlOrganizationGroupStatsPanel(UserOrganizationGroupMixin, CombinedChartMixin, StatsPanel):
    tabbed_table_template_cls = TabbedBootstrapTableTemplate
    select_widget = ""
    case_subqueries = {}
    default_subquery = ""
    show_table_index = False
    show_initial_table = False

    @property
    def variable_dim_label(self):
        if getattr(self, self.variable_widget) and not self.organizations:
            return self.widgets[self.variable_widget].alt_title
        elif self.organizations:
            return self.queryset_widgets["organizations"]["variable_label"]

    def has_perm(self):
        perms = (self.user.agent,)
        return any(perms)

    @property
    def is_regroupable_df(self):
        return self.organizations and getattr(self, self.select_widget)

    @staticmethod
    def dictfetchall(cursor):
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def post_process_table_df(self):
        return self.cached_df.copy()

    def post_process_chart_df(self):
        df = self.cached_df.copy()
        if self.is_regroupable_df:
            for organization in self.organizations_names:
                org_data = df.filter(regex=rf"^{organization}")
                to_delete = list(org_data.columns)
                df[organization] = org_data.sum(axis=1)
                df.drop(to_delete, axis=1, inplace=True)
        return df

    def table_template(self, df):
        if self.is_regroupable_df:
            template = self.tabbed_table_template_cls(df, self.organizations_names)
        else:
            template = super().table_template(df)
        return template

    def chart(self):
        return self.get_combined_chart(self.post_process_chart_df())

    def get_sql_filter_params(self):
        if self.organizations:
            filter_query = "o.id = ANY(%s)"
            query_param = [org[0] for org in self.organizations]
        elif self.user.extra_agent_of:
            filter_query = "a.user_id = %s"
            query_param = self.user.extra_agent_of_id
        else:
            filter_query = "a.user_id = %s"
            query_param = self.user.pk
        return filter_query, query_param

    def get_main_sql(self, filter_query, select_query):
        raise NotImplementedError

    def get_select_query(self):
        select_widget_options = getattr(self, self.select_widget, None)
        if select_widget_options:
            select_query = ", ".join([self.case_subqueries[option[0]] for option in select_widget_options])
        else:
            select_query = self.default_subquery
        return select_query

    def construct_raw_sql(self):
        select_query = self.get_select_query()
        filter_query, query_param = self.get_sql_filter_params()
        sql = self.get_main_sql(filter_query, select_query)
        return sql, query_param

    def execute_raw_sql(self):
        sql, query_param = self.construct_raw_sql()
        with connections["default"].cursor() as cursor:
            cursor.execute(sql, [query_param])
            query_result = self.dictfetchall(cursor)
        return query_result

    def get_queryset(self):
        qs = self.execute_raw_sql()
        self.set_organizations_names(qs)
        return qs

    def get_institutions(self, qs):
        selected_orgs_options = self.organizations or []
        qs_organization_names = set([itm["organization"] for itm in qs])
        return qs_organization_names, selected_orgs_options

    def set_organizations_names(self, qs):
        organizations_names, selected_orgs_options = self.get_institutions(qs)
        if not organizations_names and selected_orgs_options:
            selected_ids = [org[0] for org in selected_orgs_options]
            organizations_names = list(Organization.objects.filter(pk__in=selected_ids).values_list("title", flat=True))
        self.organizations_names = organizations_names

    def get_dataframe(self):
        qs = self.qs

        selected_options = getattr(self, self.select_widget, []) or []
        options_visible_labels = list(
            filter(
                lambda elem: elem[1] in selected_options,
                getattr(self.param, self.select_widget).names.items(),
            )
        )

        data_dicts = self.get_datadicts(selected_options, options_visible_labels)
        data = {_("Entry"): [], _("Period"): []}
        try:
            periods = prepare_time_periods(qs[0]["period"], qs[-1]["period"], self.timeperiod)
            values_dict = {data_label: [] for data_label in data_dicts.keys()}
            data.update(values_dict)
            _data = OrderedDict({itm: {_("Entry"): i, "values": dict(**data_dicts)} for i, itm in enumerate(periods)})
            self.reformat_data(_data, periods, qs, selected_options, options_visible_labels)

            for period, period_details in _data.items():
                data[_("Entry")].append(period_details[_("Entry")])
                data[_("Period")].append(period)
                for value_label, value in period_details["values"].items():
                    data[value_label].append(value)
        except IndexError:
            values_dict = {data_label: [0] for data_label in data_dicts.keys()}
            data[_("Entry")].append(0)
            data[_("Period")].append(_("None"))
            data.update(values_dict)
        df = pd.DataFrame(data=data)
        df.set_index(_("Entry"), inplace=True)
        df = self.reformat_dataframe(
            df,
            selected_options=selected_options,
            options_visible_labels=options_visible_labels,
            data_dicts=data_dicts,
        )
        return df

    def get_count_key_label(self, val):
        raise NotImplementedError

    def reformat_data(self, data_dicts, periods, qs, selected_options, options_visible_labels):
        raise NotImplementedError


class DataCountByTimePeriodForGroup(RawSqlOrganizationGroupStatsPanel):

    def get_datadicts(self, selected_options, options_visible_labels):
        if selected_options:
            data_dicts = {}
            for org in self.organizations_names:
                data_dicts.update({f"{org}-{option_label[0]}": 0 for option_label in options_visible_labels})
        else:
            data_dicts = {org: 0 for org in self.organizations_names}
        return data_dicts

    def reformat_data(self, _data, periods, qs, selected_options, options_visible_labels):
        for item in qs:
            period = format_time_period(item["period"], self.timeperiod)
            if selected_options:
                org = item["organization"]
                for option_key, val in options_visible_labels:
                    count_key = self.get_count_key_label(val)
                    key = f"{org}-{option_key}"
                    _data[period]["values"][key] += int(item[f"{count_key}_count"])
            else:
                _data[period]["values"][item["organization"]] += int(item["all_count"])
        return _data

    def reformat_dataframe(self, df, **kwargs):
        selected_options = kwargs["selected_options"]
        options_visible_labels = kwargs["options_visible_labels"]
        df = df.replace(to_replace=0, method="ffill")
        if not self.organizations and not selected_options:
            to_delete = list(self.organizations_names)
            df[_("Number")] = df.sum(axis=1)
            df.drop(to_delete, axis=1, inplace=True)
        elif not self.organizations:
            for visible_label in options_visible_labels:
                viz_df = df.filter(regex=rf".*-{visible_label[0]}")
                df[visible_label[0]] = viz_df.sum(axis=1)
                to_delete = list(viz_df.columns)
                df.drop(to_delete, axis=1, inplace=True)
        return df


class NewDataByTimePeriodForGroup(RawSqlOrganizationGroupStatsPanel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.p_map = {
            "absolute": _("Number"),
            "percentage": _("Percent"),
        }

    def get_institutions(self, qs):
        qs_organization_names, selected_orgs_options = super().get_institutions(qs)
        if not selected_orgs_options:
            qs_organization_names = []
        return qs_organization_names, selected_orgs_options

    def get_datadicts(self, selected_options, options_visible_labels):
        if selected_options and self.organizations_names:
            data_dicts = {}
            for org in self.organizations_names:
                data_dicts.update({f"{org}-{option_label[0]}": 0 for option_label in options_visible_labels})
        elif self.organizations_names:
            data_dicts = {org: 0 for org in self.organizations_names}
        elif selected_options:
            data_dicts = {option_label[0]: 0 for option_label in options_visible_labels}
        else:
            data_dicts = {self.p_map[self.presentation_type]: 0}
        return data_dicts

    def reformat_data(self, _data, periods, qs, selected_options, options_visible_labels):
        for item in qs:
            period = format_time_period(item["period"], self.timeperiod)
            if selected_options and self.organizations_names:
                org = item["organization"]
                for option_key, val in options_visible_labels:
                    count_key = self.get_count_key_label(val)
                    key = f"{org}-{option_key}"
                    _data[period]["values"][key] += int(item[f"{count_key}_count"])
            elif selected_options:
                for key, val in options_visible_labels:
                    count_key = self.get_count_key_label(val)
                    _data[period]["values"][key] += int(item[f"{count_key}_count"])
            elif self.organizations_names:
                _data[period]["values"][item["organization"]] += int(item["all_count"])
            else:
                _data[period]["values"][self.p_map[self.presentation_type]] += int(item["all_count"])
        return _data

    def reformat_dataframe(self, df, **kwargs):
        data_dicts = kwargs["data_dicts"]
        if self.presentation_type == "percentage":
            for v_key in data_dicts.keys():
                df[f"{v_key}_cumsum"] = df[v_key].shift().cumsum()
                df[f"{v_key}_cumsum"] = df[f"{v_key}_cumsum"].fillna(0)
                df[v_key] = np.where(
                    df[f"{v_key}_cumsum"] == 0,
                    0,
                    (df[v_key] / df[f"{v_key}_cumsum"]) * 100,
                )
                df[v_key] = df[v_key].round(2)
                del df[f"{v_key}_cumsum"]
        return df


class ChartPanel(StatsPanel):
    model = None
    y_axis_attr_name = ""
    x_axis_attr_name = ""
    use_index = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.init_labels()

    def has_perm(self):
        perms = (
            self.user.is_superuser,
            self.user.is_editor,
            self.user.agent,
        )

        return any(perms)

    def get_dataframe(self):
        data = {}
        results = self.get_results()
        for _i, inst in enumerate(results):
            idx = data.setdefault(self.index_label, [])
            idx.append(_i + 1)
            n = data.setdefault(self.x_axis_label, [])
            n.append(inst[self.x_axis_attr_name])
            i = data.setdefault(self.y_axis_label, [])
            i.append(inst[self.y_axis_attr_name])
        if not data:
            data[self.index_label] = [1]
            data[self.x_axis_label] = [_("None")]
            data[self.y_axis_label] = [0]

        df = pd.DataFrame(data)
        df.set_index(self.index_label, inplace=True)
        return df

    def get_bar_kwargs(self):
        common_kwargs = self.get_chart_kwargs()
        kwargs = {
            "stacked": True,
            "legend": "bottom",
        }
        kwargs.update(**common_kwargs)
        if self.use_index:
            kwargs["use_index"] = self.use_index
            kwargs["x"] = self.index_label
        return kwargs

    def chart(self):
        chart = self.cached_df.hvplot.bar(
            hover_cols=[
                self.y_axis_label,
                self.x_axis_label,
            ],
            **self.get_bar_kwargs(),
        )
        chart.opts(xlabel="", axiswise=True)

        return chart

    def init_labels(self):
        self.index_label = ""
        self.y_axis_label = "Oś y"
        self.x_axis_label = "Oś x"


class RankingPanel(ChartPanel):
    top_count = 10

    def init_labels(self):
        super().init_labels()
        self.index_label = _("Entry")

    def get_results(self):
        qs = self.get_queryset()
        sql = str(qs.query)
        start = time()
        result = qs[: self.top_count]
        total = time() - start
        q_log.debug("%s;%.2f;%s" % (self.name, total, sql))
        return result
