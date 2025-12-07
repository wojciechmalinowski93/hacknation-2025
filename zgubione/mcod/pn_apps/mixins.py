from django.db.models import Q
from django.utils.translation import gettext as _

from mcod.pn_apps.params import UserGroupProvidersParamsWidget


class UserFilterMixin:

    def get_user_query(self, q):
        user_q = Q(**{q: self.user.pk})
        if self.user.extra_agent_of_id:
            user_q |= Q(**{q: self.user.extra_agent_of_id})
        return user_q


class UserOrganizationGroupMixin(UserFilterMixin):
    queryset_widgets = {
        "organizations": {
            "widget_cls": UserGroupProvidersParamsWidget,
            "name": "Instytucje",
            "variable_label": "Instytucja",
        }
    }

    def get_queryset_widget_kwargs(self):
        user_q = self.get_user_query("agents__pk")
        return {"organizations": {"query_params": user_q}}


class CombinedChartMixin:

    def get_combined_chart(self, df):
        line_chart = df.plot(legend="bottom", x=_("Period"), **self.get_chart_kwargs()).opts(default_tools=[])
        cols = list(df.columns[1:])
        scatter_chart = df.plot.scatter(legend=None, x=_("Period"), y=cols, **self.get_chart_kwargs()).opts(default_tools=[])

        combined_charts = line_chart * scatter_chart
        combined_charts.opts(
            show_legend=False,
            xlabel="",
            shared_axes=False,
            xrotation=90,
        )
        return combined_charts
