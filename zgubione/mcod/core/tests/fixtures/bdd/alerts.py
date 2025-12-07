from pytest_bdd import given

from mcod.alerts.factories import AlertFactory


@given("alert")
def alert():
    return AlertFactory.create()
