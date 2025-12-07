from typing import Dict, Optional, Type

from django.conf import settings

from mcod.resources.score_computation.calculators.calculator_json import calculate_score_for_json
from mcod.resources.score_computation.calculators.calculator_xml import (
    calculate_score_for_rdf,
    calculate_score_for_xml,
)
from mcod.resources.score_computation.common import OpennessScoreCalculator

extension_to_score_calculator: Dict[str, Type[OpennessScoreCalculator]] = {
    "json": calculate_score_for_json,
    "xml": calculate_score_for_xml,
}

_for_rdf = {extension: calculate_score_for_rdf for extension in settings.RDF_FORMAT_TO_MIMETYPE.keys() if extension != "xml"}
extension_to_score_calculator.update(_for_rdf)


def get_calculator_for_extension(extension: str) -> Optional[Type[OpennessScoreCalculator]]:
    return extension_to_score_calculator.get(extension)


__all__ = (get_calculator_for_extension,)
