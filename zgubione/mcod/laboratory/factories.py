import random
import uuid

import factory

from mcod.core.registries import factories_registry
from mcod.laboratory import models
from mcod.resources.factories import get_csv_file


class LabEventFactory(factory.django.DjangoModelFactory):
    title = factory.Faker("text", max_nb_chars=80, locale="pl_PL")
    notes = factory.Faker("paragraph", nb_sentences=5)
    event_type = factory.Faker("random_element", elements=[x[0] for x in models.EVENT_TYPES])
    execution_date = factory.Faker("past_date", start_date="-60d")
    status = "published"

    @factory.post_generation
    def reports(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for report in extracted:
                self.reports.add(report)

    class Meta:
        model = models.LabEvent


class ReportFactory(factory.django.DjangoModelFactory):
    lab_event = factory.SubFactory(LabEventFactory)
    link = factory.Faker("url")
    file = factory.django.FileField(from_func=get_csv_file, filename="{}.csv".format(str(uuid.uuid4())))

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        report = super()._create(model_class, *args, **kwargs)

        report_type = kwargs.get("report_type", random.choice(("file", "link")))
        if report_type == "file":
            report.link = None
        else:
            report.file = None

        return report

    class Meta:
        model = models.LabReport


factories_registry.register("lab_event", LabEventFactory)
factories_registry.register("report", ReportFactory)
