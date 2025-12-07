import pytest

from mcod.core.registries import csv_serializers_registry
from mcod.datasets.models import Dataset
from mcod.datasets.serializers import DatasetCSVSchema
from mcod.organizations.models import Organization
from mcod.organizations.serializers import InstitutionCSVSchema
from mcod.resources.models import Resource
from mcod.resources.serializers import ResourceCSVSchema
from mcod.schedules.models import UserScheduleItem
from mcod.schedules.serializers import UserScheduleItemCSVSerializer
from mcod.showcases.models import ShowcaseProposal
from mcod.showcases.serializers import ShowcaseProposalCSVSerializer
from mcod.suggestions.serializers import (
    DatasetCommentCSVSerializer,
    DatasetSubmissionCSVSerializer,
    ResourceCommentCSVSerializer,
)
from mcod.users.models import User

from mcod.suggestions.models import (  # isort: skip
    DatasetComment,
    DatasetSubmission,
    ResourceComment,
)

from mcod.users.serializers import (  # isort: skip
    DefaultUserCSVSerializer,
    UserLocalTimeCSVSerializer,
)

EXPECTED_REGISTRY = {
    Dataset: DatasetCSVSchema,
    DatasetComment: DatasetCommentCSVSerializer,
    DatasetSubmission: DatasetSubmissionCSVSerializer,
    User: DefaultUserCSVSerializer,
    Organization: InstitutionCSVSchema,
    ResourceComment: ResourceCommentCSVSerializer,
    Resource: ResourceCSVSchema,
    ShowcaseProposal: ShowcaseProposalCSVSerializer,
    UserScheduleItem: UserScheduleItemCSVSerializer,
}


class TestSerializersRegistry:
    @pytest.mark.parametrize("model, serializer", EXPECTED_REGISTRY.items())
    def test_csv_serializers_registry(self, model, serializer):
        registered_serializer = csv_serializers_registry.get_serializer(model)
        assert registered_serializer == serializer

    def test_no_extra_registered_serializers(self):
        registry_serializers_count = len(csv_serializers_registry.items())
        expected_serializers_count = len(EXPECTED_REGISTRY)
        assert registry_serializers_count == expected_serializers_count

    def test_user_localtime_csv_serializer_is_not_registered(self):
        registered_serializers = [serializer for _, serializer in csv_serializers_registry.items()]
        assert UserLocalTimeCSVSerializer not in registered_serializers
