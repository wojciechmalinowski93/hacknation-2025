from pytest_bdd import given, parsers

from mcod.categories.factories import CategoryFactory


@given(parsers.parse("category with id {category_id:d}"))
def category_with_id(category_id):
    return CategoryFactory.create(id=category_id, title="Category {}".format(category_id))
