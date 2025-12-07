from goodtables.error import Error
from goodtables.registry import check

ZERO_DATA_ROWS = "zero-data-rows"
ZERO_DATA_ROWS_MSG = "Brak wierszy z danymi"


@check(ZERO_DATA_ROWS, type="custom", context="body")
class ZeroDataRows:
    def __init__(self, **kwargs):
        self.__rows_count = 0

    def check_row(self, cells):
        self.__rows_count += 1

    def check_table(self):
        errors = []
        if self.__rows_count == 0:
            errors.append(
                Error(
                    ZERO_DATA_ROWS,
                    row_number=0,
                    message=ZERO_DATA_ROWS_MSG,
                )
            )
        return errors
