from bokeh.core.properties import Bool, Either, Int, List, String, Tuple
from bokeh.models.widgets import InputWidget, RadioButtonGroup


class BootstrapSelect(InputWidget):
    __javascript__ = [
        "https://cdn.jsdelivr.net/npm/bootstrap-select@1.13.14/dist/js/bootstrap-select.min.js",
        "https://cdn.jsdelivr.net/npm/bootstrap-select@1.13.14/dist/js/i18n/defaults-pl_PL.min.js",
    ]
    __css__ = ["https://cdn.jsdelivr.net/npm/bootstrap-select@1.13.14/dist/css/bootstrap-select.min.css"]
    alt_title = String(default="")
    options = List(Tuple(String, Tuple(Either(Int, String), String)))
    value = List(Tuple(Either(Int, String), String))
    actions_box = Bool(default=False)
    live_search = Bool(default=False)
    select_all_at_start = Bool(default=False)
    count_selected_text = String(default="")
    none_selected_text = String(default="")
    selected_text_format = String(default="")
    none_results_text = String(default="")


class ExtendedRadioButtonGroup(RadioButtonGroup):
    pass
