class NoDataForReportException(Exception):
    def __init__(self, message="No data found for the report"):
        super().__init__(message)
