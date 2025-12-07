import random

import factory
from django_celery_results.models import TaskResult


class TaskResultFactory(factory.django.DjangoModelFactory):
    status = factory.LazyFunction(lambda: random.choice(["SUCCESS", "FAILURE", "PENDING"]))
    task_id = factory.Faker("random_letters", length=10)

    class Meta:
        model = TaskResult
