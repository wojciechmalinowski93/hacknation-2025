from dataclasses import dataclass
from typing import Callable, Literal, Optional, Union

from django.db.models.fields.files import FieldFile

# typing here reflects https://5stardata.info, while adding a missing value
MissingOpennessScoreValue = Literal[0]
OpennessScoreValue = Literal[1, 2, 3, 4, 5]
OptionalOpennessScoreValue = Union[MissingOpennessScoreValue, OpennessScoreValue]
Source = Union[str, FieldFile]


@dataclass
class SourceData:
    extension: str
    data: Optional[bytes] = None
    res_link: Optional[str] = None
    link_header: Optional[str] = None
    is_archive: bool = False


OpennessScoreCalculator = Callable[[SourceData], OpennessScoreValue]
