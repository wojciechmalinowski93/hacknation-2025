from bokeh.core.properties import Bool
from bokeh.models.layouts import Column


class ExtendedColumn(Column):
    aria_hidden = Bool(False)
