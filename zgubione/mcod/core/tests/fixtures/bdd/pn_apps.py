import json
from pydoc import locate
from unittest.mock import MagicMock

import panel as pn
from bokeh.document import Document
from pytest_bdd import given, parsers, then, when

from mcod.core.tests.fixtures.users import create_user_with_params
from mcod.pn_apps.stats_app import app
from mcod.pn_apps.widgets import BootstrapSelectWidget


def create_context_with_user(user, headers=None):
    headers_ = {"user-agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:99.0) Gecko/20100101 Firefox/99.0"}
    cookies_ = {"currentLang": "pl"}
    if headers is not None and isinstance(headers, dict):
        headers_.update(headers)
    mocked__request = MagicMock()
    mocked_request = MagicMock()
    mocked_context = MagicMock()
    mocked__request.user = user
    mocked_request._request = mocked__request
    mocked_request.headers = headers_
    mocked_request.cookies = cookies_
    mocked_context.request = mocked_request
    return mocked_context


def create_stats_document_for_user(user_type, params=None):
    created_user = create_user_with_params(user_type, params)
    session_context = create_context_with_user(created_user)
    doc = Document()
    doc._session_context = MagicMock(return_value=session_context)
    return doc


@given(parsers.parse("stats document viewed by {user_type}"))
def stats_document_for_admin(user_type, ctx):
    doc = create_stats_document_for_user(user_type)
    ctx["document"] = doc
    return ctx


@given(parsers.parse("stats document viewed by agent created with params {params}"))
def stats_document_for_admin_with_params(params, ctx):
    doc = create_stats_document_for_user("agent user", params)
    ctx["document"] = doc
    return ctx


@then("Figures are rendered without errors")
def figures_rendered(ctx):
    try:
        app(ctx["document"])
        assert True
    except Exception as err:
        assert False, f"Figures rendering raised an error: {err}"


@given(parsers.parse("Chart user {user_type}"))
def chart_user(user_type, ctx):
    created_user = create_user_with_params(user_type)
    ctx["user"] = created_user
    return ctx


@given(parsers.parse("chart agent user created with params {params}"))
def chart_agent_user(ctx, params):
    created_user = create_user_with_params("agent user", params)
    ctx["user"] = created_user
    return ctx


@given(parsers.parse("chart panel of class {chart_cls}"))
def create_chart_panel(chart_cls, ctx):
    doc = Document()
    charts_kwargs = {
        "user": ctx["user"],
        "doc": doc,
        "lang": "pl",
        "fav_charts_widget": pn.widgets.TextInput(value=json.dumps(ctx["user"].fav_charts)),
    }
    stats_module = "mcod.pn_apps.stats_app"
    chart_path = f"{stats_module}.{chart_cls}"
    chart_model = locate(chart_path)
    chart_instance = chart_model(name=f"Test chart {chart_cls}", **charts_kwargs)
    chart_panel = chart_instance.panel()
    ctx["chart_panel"] = chart_panel
    ctx["chart_instance"] = chart_instance
    return ctx


@when(parsers.parse("chart select widget has set {selected_options}"))
def set_select_widget_value(selected_options, ctx):
    widgets_column = ctx["chart_panel"].objects[1]
    if len(ctx["chart_panel"].objects) == 5:
        chart_widgets = widgets_column.objects
        if hasattr(chart_widgets[0], "objects"):
            chart_widgets = chart_widgets[0].objects
    else:
        chart = widgets_column.objects[0]
        chart_widgets = chart.objects
    selected_value = [(v, "") for v in selected_options.split(",")]
    for widget in chart_widgets:
        if isinstance(widget, BootstrapSelectWidget) and widget.alt_title != "Instytucje":
            select_widget = widget
            select_widget.value = selected_value
    return ctx


@then(parsers.parse("chart dataframe contains columns {headers}"))
def dataframe_contains_columns(ctx, headers):
    expected_columns = set(headers.split(","))
    current_columns = set(ctx["chart_instance"].cached_df.columns)
    assert expected_columns <= current_columns, f"Expected columns where: {headers}, but current are: {current_columns}"
