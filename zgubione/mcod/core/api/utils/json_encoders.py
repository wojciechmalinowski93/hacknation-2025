import json
from datetime import date, datetime, time

from elasticsearch_dsl import AttrList


class APIEncoder(json.JSONEncoder):
    def default(self, data):
        # DateTime to ISO
        if isinstance(data, (datetime, time)):
            return data.isoformat("T")
        if isinstance(data, date):
            return data.isoformat()

        # elasticsearch AttrList to tuple
        if isinstance(data, AttrList):
            return tuple(data)
