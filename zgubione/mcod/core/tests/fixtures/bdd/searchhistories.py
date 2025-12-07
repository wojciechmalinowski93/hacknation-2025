from elasticsearch_dsl import Q
from pytest_bdd import given, parsers, then

from mcod.searchhistories.documents import SearchHistoriesDoc
from mcod.searchhistories.factories import SearchHistoryFactory


@given(parsers.parse("{num:d} search histories for admin"))
def search_histories_for_admin(num, admin):
    SearchHistoryFactory.create_batch(num, user=admin)


@then(parsers.parse("search history list in response is sorted by {sort}"))
def searchhistory_list_in_response_is_sorted_by(context, sort):
    data = context.response.json["data"]
    if "title" in sort:
        order = "desc" if sort.startswith("-") else "asc"
        field = sort[1:] if sort.startswith("-") else sort
        sort = {field: {"order": order, "nested": {"path": "title"}}}
    _sorted = (
        SearchHistoriesDoc()
        .search()
        .filter("nested", path="user", query=Q("match", **{"user.id": context.user.id}))
        .sort(sort)[: len(data)]
    )
    items = [int(x["id"]) for x in data]
    sorted_items = [x.id for x in _sorted]
    assert items == sorted_items, "response data should be {}, but is {}".format(sorted_items, items)
