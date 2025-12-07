import datetime

import pytest

from mcod.resources.indexed_data import prepare_item


@pytest.mark.parametrize(
    "value,type,output",
    [
        (
            datetime.datetime(2020, 2, 2, 0, 0),
            None,
            datetime.datetime(2020, 2, 2, 0, 0),
        ),
        (datetime.datetime(2020, 2, 2, 0, 0), "date", "2020-02-02"),
    ],
)
def test_prepare_item(value, type, output):
    assert prepare_item(value, type) == {"repr": output, "val": output}
