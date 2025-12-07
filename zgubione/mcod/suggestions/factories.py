import factory

from mcod.core.registries import factories_registry
from mcod.datasets.factories import DatasetFactory
from mcod.resources.factories import ResourceFactory
from mcod.suggestions.models import (
    AcceptedDatasetSubmission,
    DatasetComment,
    DatasetSubmission,
    ResourceComment,
    SubmissionFeedback,
)


class DatasetSubmissionFactory(factory.django.DjangoModelFactory):
    title = factory.Faker("text", max_nb_chars=15, locale="pl_PL")
    notes = factory.Faker("paragraph", nb_sentences=5)

    class Meta:
        model = DatasetSubmission


class AcceptedDatasetSubmissionFactory(factory.django.DjangoModelFactory):
    title = factory.Faker("text", max_nb_chars=15, locale="pl_PL")
    notes = factory.Faker("paragraph", nb_sentences=5)

    class Meta:
        model = AcceptedDatasetSubmission


class DatasetCommentFactory(factory.django.DjangoModelFactory):
    dataset = factory.SubFactory(DatasetFactory)
    comment = factory.Faker("paragraph", nb_sentences=5)

    class Meta:
        model = DatasetComment


class ResourceCommentFactory(factory.django.DjangoModelFactory):
    resource = factory.SubFactory(ResourceFactory)
    comment = factory.Faker("paragraph", nb_sentences=5)

    class Meta:
        model = ResourceComment


class SubmissionFeedbackFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = SubmissionFeedback


factories_registry.register("datasetsubmission", DatasetSubmissionFactory)
factories_registry.register("accepteddatasetsubmission", AcceptedDatasetSubmissionFactory)
factories_registry.register("datasetcomment", DatasetCommentFactory)
factories_registry.register("resourcecomment", ResourceCommentFactory)
factories_registry.register("submissionfeedback", SubmissionFeedbackFactory)
