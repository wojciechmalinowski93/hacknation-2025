import locale
from datetime import datetime, timedelta
from pydoc import locate

import holoviews as hv
import pandas as pd
from bokeh.themes.theme import Theme
from dateutil.rrule import MONTHLY, YEARLY, rrule
from django.conf import settings
from django.utils import timezone

from mcod.core import storages


def set_locale(locale_code):
    try:
        locale.setlocale(locale.LC_ALL, locale_code)
    except locale.Error:
        locale.setlocale(locale.LC_ALL, "en_GB.UTF-8")


def format_time_period(dt, period):
    if period == "month":
        return dt.strftime("%b %Y").title()
    elif period == "quarter":
        quarter = pd.Timestamp(dt).quarter
        return f"Q{quarter} {dt.year}"
    else:
        return str(dt.year)


def prepare_time_periods(start_date, end_date, period):
    freq = MONTHLY
    interval = 1
    if period == "year":
        freq = YEARLY
        since_year = start_date.year
        to_year = end_date.year
        since = start_date.replace(day=1, month=1, year=since_year)
        to = end_date.replace(day=31, month=12, year=to_year)
    elif period == "quarter":
        interval = 3
        since_month = first_month_of_quarter(start_date.month)
        to_month = first_month_of_quarter(end_date.month)
        since = start_date.replace(day=1, month=since_month)
        to = end_date.replace(day=2, month=to_month)
    else:
        end_date = end_date + timedelta(days=1)
        since = start_date
        to = end_date
    result = [format_time_period(d, period) for d in rrule(freq=freq, interval=interval, dtstart=since, until=to)]

    return result


def first_month_of_quarter(month):
    return month - (month - 1) % 3


def chart_thumb_path(user, slot=1):
    storage = storages.get_storage("chart_thumbs")
    delta = timezone.timedelta(days=36500)
    token = user._get_or_create_token(2, expiration_delta=delta)
    return storage.path(f"{token}-{slot}.png")


def change_theme(style_name):
    theme_path = "mcod.pn_apps.bokeh.themes."
    try:
        theme_file_name = style_name.replace("-", "_")
        full_path = theme_path + theme_file_name
        selected_theme = locate(full_path)
        json_theme = selected_theme.json
    except AttributeError:
        json_theme = {}
    hv.renderer("bokeh").theme = Theme(json=json_theme)


def register_event_widgets(charts, extra_kwargs):
    event_widgets = []
    widgets_base_path = "mcod.pn_apps.widgets"
    event_settings = getattr(settings, "STATS_EVENTS", [])
    for event_details in event_settings:
        widget_path = f'{widgets_base_path}.{event_details["widget_cls"]}'
        event_widget_cls = locate(widget_path)
        instance_kwargs = {"charts": charts, "name": event_details["event_name"]}
        instance_kwargs.update(extra_kwargs.get(event_details["event_name"], {}))
        event_widget = event_widget_cls(**instance_kwargs)
        event_widget.param.watch(event_widget.event_callback, ["value"])
        event_widgets.append(event_widget)
    return event_widgets


def reformat_time_period(timestamp):
    lookup_table = {
        "stycznia": "Styczeń",
        "lutego": "Luty",
        "marca": "Marzec",
        "kwietnia": "Kwiecień",
        "maja": "Maj",
        "czerwca": "Czerwiec",
        "lipca": "Lipiec",
        "sierpnia": "Sierpień",
        "września": "Wrzesień",
        "października": "Październik",
        "listopada": "Listopad",
        "grudnia": "Grudzień",
    }
    try:
        try:
            timestamp = datetime.strptime(timestamp, "%b %Y").strftime("%B %Y")
        except TypeError:
            timestamp = timestamp.strftime("%B %Y")
        date_parts = timestamp.split(" ")
        month_name = lookup_table.get(date_parts[0], date_parts[0])
        timestamp = timestamp.replace(date_parts[0], month_name)
    except ValueError:
        pass
    return timestamp
