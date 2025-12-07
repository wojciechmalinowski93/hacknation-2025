import dpath
from pytest_bdd import parsers, then


@then(parsers.parse("dashboard api's response planned courses is {planned}"))
def dashboard_planned_courses(context, planned):
    planned = int(planned)
    value = dpath.util.get(context.response.json, "/meta/aggregations/academy/planned")
    assert value == planned


@then(parsers.parse("dashboard api's response current courses is {current}"))
def dashboard_current_courses(context, current):
    current = int(current)
    value = dpath.util.get(context.response.json, "/meta/aggregations/academy/current")
    assert value == current


@then(parsers.parse("dashboard api's response finished courses is {finished}"))
def dashboard_finished_courses(context, finished):
    finished = int(finished)
    value = dpath.util.get(context.response.json, "/meta/aggregations/academy/finished")
    assert value == finished
