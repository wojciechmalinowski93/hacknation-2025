import random
import string
from uuid import uuid4

import pandas as pd
import param
from django.template.loader import render_to_string
from django.utils.translation import gettext as _
from panel.util import isIn
from panel.widgets import RadioButtonGroup
from panel.widgets.select import SelectBase, _MultiSelectBase

from mcod.pn_apps.bokeh.widgets import (
    BootstrapSelect as _BootstrapSelect,
    ExtendedRadioButtonGroup as _BkExtendedRadioButtonGroup,
)


class BootstrapSelectWidget(_MultiSelectBase):
    alt_title = param.String(default="")
    actions_box = param.Boolean(default=False)
    live_search = param.Boolean(default=False)
    select_all_at_start = param.Boolean(default=False)
    none_selected_text = param.String(default="")
    count_selected_text = param.String(default="")
    selected_text_format = param.String(default="")
    none_results_text = param.String(default="")

    _widget_type = _BootstrapSelect

    def _process_param_change(self, msg):
        msg = super(SelectBase, self)._process_param_change(msg)
        values = self.values
        if "value" in msg:
            _values = [value for value in msg["value"] if isIn(value, values)]
            msg["value"] = _values
        else:
            msg["value"] = self.value

        if "options" in msg:
            msg["options"] = list(self.options.items())

        return msg

    def _process_property_change(self, msg):
        msg = super(SelectBase, self)._process_property_change(msg)
        if "value" in msg:
            values = self.values
            if not values:
                pass
            elif msg["value"] is None:
                msg["value"] = values[0]
            else:
                _values = [value for value in msg["value"] if isIn(value, values)]
                msg["value"] = _values
        msg.pop("options", None)
        return msg


class BaseTableTemplate:
    template_path = None

    def __init__(self, dataframe):
        self.df = dataframe

    def get_context_data(self):
        return {
            "df": self.df,
        }

    def _repr_html_(self):
        return render_to_string(self.template_path, self.get_context_data())


class BootstrapTableTemplate(BaseTableTemplate):
    template_path = "pn_apps/bootstrap_table.html"

    def __init__(self, dataframe, caption=None, show_table_index=True):
        self.caption = caption
        self.show_table_index = show_table_index
        self.table_id = str(uuid4())
        self.paginate = len(dataframe.index) > 10
        super().__init__(dataframe)

    def get_context_data(self):
        context_data = super().get_context_data()
        context_data.update(
            {
                "caption": self.caption,
                "show_table_index": self.show_table_index,
                "table_id": self.table_id,
                "paginate": self.paginate,
            }
        )
        return context_data


class TabbedBootstrapTableTemplate(BaseTableTemplate):
    template_path = "pn_apps/tabbed_bootstrap_table.html"

    def __init__(self, dataframe, tabs):
        self.tabs_labels = tabs
        super().__init__(dataframe)

    def split_dataframe(self):
        tabs = []
        tabs_nav = []
        periods_df = self.df[_("Period")]
        chars = string.ascii_uppercase + string.ascii_lowercase
        for label in self.tabs_labels:
            label_df = self.df.filter(regex=rf"^{label}")
            current_columns = list(label_df.columns)
            rename_mapping = {col: col.split("-")[-1] for col in current_columns}
            label_df.rename(columns=rename_mapping, inplace=True)
            sub_df = pd.concat(
                [periods_df.reset_index(drop=True), label_df.reset_index(drop=True)],
                axis=1,
            )
            pane_id = "".join(random.choice(chars) for _ in range(36))
            table = BootstrapTableTemplate(sub_df, show_table_index=False)._repr_html_()
            tabs.append({"pane_id": pane_id, "table": table})
            tabs_nav.append({"pane_id": pane_id, "label": label})
        return tabs, tabs_nav

    def get_context_data(self):
        context_data = super().get_context_data()
        tabs, tabs_nav = self.split_dataframe()
        context_data["tabs_nav"] = tabs_nav
        context_data["tabs"] = tabs
        context_data["tab_id"] = str(uuid4())
        return context_data


class ExtendedRadioButtonGroup(RadioButtonGroup):
    _widget_type = _BkExtendedRadioButtonGroup
