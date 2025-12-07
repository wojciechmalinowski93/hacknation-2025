import random

import dpath
from pytest_bdd import given, parsers, then

from mcod.laboratory.factories import LabEventFactory, ReportFactory


@given(parsers.parse("{researches} laboratory researches"))
def laboratory_research(researches):
    researches = int(researches)
    return LabEventFactory.create_batch(
        size=researches,
        event_type="research",
    )


@given(parsers.parse("{analyses} laboratory analyses"))
def laboratory_analysis(analyses):
    analyses = int(analyses)
    return LabEventFactory.create_batch(
        size=analyses,
        event_type="analysis",
    )


@then(parsers.parse("dashboard api's response laboratory researches is {researches}"))
def dashboard_api_response_researches(researches, context):
    researches = int(researches)
    value = dpath.util.get(context.response.json, "/meta/aggregations/lab/researches")
    assert value == researches, "researches on dashboard is %s, expected %s" % (
        value,
        researches,
    )


@then(parsers.parse("dashboard api's response laboratory analyses is {analyses}"))
def dashboard_api_response_analyses(analyses, context):
    analyses = int(analyses)
    value = dpath.util.get(context.response.json, "/meta/aggregations/lab/analyses")
    assert value == analyses, "analyses on dashboard is %s, expected %s" % (
        value,
        analyses,
    )


@given(parsers.parse("Laboratory analysis {labevent_id:d}"))
def analysis_with_id(labevent_id):
    analysis = LabEventFactory.create(
        id=labevent_id,
        title="Analysis with id: %s" % labevent_id,
        event_type="analysis",
    )
    ReportFactory.create(lab_event=analysis)
    analysis.save()
    return analysis


@given(parsers.parse("Laboratory research {labevent_id:d}"))
def research_with_id(labevent_id):
    research = LabEventFactory.create(
        id=labevent_id,
        title="Research with id: %s" % labevent_id,
        event_type="research",
    )
    ReportFactory.create(lab_event=research)
    research.save()
    return research


@given(parsers.parse("LabEvent id {labevent_id:d}"))
def labevent_with_id(labevent_id):
    lab_event = LabEventFactory.create(
        id=labevent_id,
        title="LabEvent with id: %s" % labevent_id,
        event_type=random.choice(("research", "analysis")),
    )
    ReportFactory.create(lab_event=lab_event)
    lab_event.save()
    return lab_event
