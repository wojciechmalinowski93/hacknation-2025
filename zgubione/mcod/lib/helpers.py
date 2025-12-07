import copy
import json
import logging
from typing import Any

from celery.schedules import crontab

logger = logging.getLogger("mcod")


def change_namedlist(namedlist, fields_to_change):
    """
    Make deep copy and change given fields with given values

    :param namedlist: namedlist.namedlist
    :param kwargs: dict
    :return: namedlist
    """
    new = copy.deepcopy(namedlist)
    for k, v in fields_to_change.items():
        try:
            new.__setattr__(k, v)
        except AttributeError:
            raise KeyError("Field with name {} is not in list {}".format(k, new))
    return new


def get_paremeters_from_post(POST, startswith="rule_type_", resultname="col"):
    parameters = {}
    for rule in POST:
        if rule.startswith(startswith):
            _id = int(rule.replace(startswith, "")) + 1
            col_id = f"{resultname}{_id}"
            parameters[col_id] = POST[rule]
    return parameters


def _is_valid_beat_schedule(update_dict: dict) -> bool:
    key = ""
    try:
        for k, value in update_dict.items():
            key = k
            crontab(**value)
    except (ValueError, KeyError, TypeError):
        logger.error(f"Problem with key={key} during update celerybeat schedule")
        return False
    return True


def validate_update_data_for_beat_schedule(beat_schedule_to_update: dict, update_data: str) -> bool:
    try:
        update_dict: Any = json.loads(update_data)
        if not isinstance(update_dict, dict) or update_dict == dict():
            return False

        # check if key not duplicated in update_data
        for k in update_dict.keys():
            if update_data.count('"' + k + '"') > 1:
                return False

        if not update_dict.keys() <= beat_schedule_to_update.keys():
            # there is a key in update_dict which is not present in beat_schedule_to_update
            return False

        return _is_valid_beat_schedule(update_dict)
    except json.decoder.JSONDecodeError:
        return False
