from pytest_bdd import given, parsers, then

from mcod.core.tests.fixtures import *  # noqa
from mcod.datasets.documents import DatasetDocument


@then(parsers.parse("datasets list in response is sorted by {sort}"))
def datasets_list_in_response_is_sorted_by(context, sort):
    data = context.response.json["data"]
    if "title" in sort:
        order = "desc" if sort.startswith("-") else "asc"
        field = sort[1:] if sort.startswith("-") else sort
        sort = {field: {"order": order, "nested": {"path": "title"}}}
    _sorted = DatasetDocument().search().filter("term", status="published").sort(sort)[: len(data)]
    items = [int(x["id"]) for x in data]
    sorted_items = [x.id for x in _sorted]
    assert items == sorted_items


@given("dataset with tabular resource")
def dataset_with_tabular_resource(buzzfeed_fakenews_resource):
    return buzzfeed_fakenews_resource.dataset


@given("dataset with remote file resource")
def dataset_with_remote_file_resource(remote_file_resource):
    return remote_file_resource.dataset


@given("dataset with local file resource")
def dataset_with_local_file_resource(local_file_resource):
    return local_file_resource.dataset
