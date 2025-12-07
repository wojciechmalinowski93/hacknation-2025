from pytest_bdd import given, parsers

from mcod.histories.factories import LogEntryFactory


@given(parsers.parse("{num:d} log entries"))
def num_of_log_entries(num):
    return LogEntryFactory.create_batch(num)
