import param
from panel.layout import ListPanel

from mcod.pn_apps.bokeh.layouts import ExtendedColumn as BkExtendedColumn


class ExtendedColumn(ListPanel):
    _bokeh_model = BkExtendedColumn
    aria_hidden = param.Boolean(default=False)
