import factory

from mcod.core.registries import factories_registry
from mcod.newsletter.models import Newsletter, Submission, Subscription
from mcod.users.factories import AdminFactory


class NewsletterFactory(factory.django.DjangoModelFactory):
    title = factory.Faker("company", locale="pl_PL")
    planned_sending_date = factory.Faker("future_date", end_date="+30d")
    created_by = factory.SubFactory(AdminFactory)

    class Meta:
        model = Newsletter


class SubscriptionFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory(AdminFactory)
    email = factory.Faker("email", locale="pl_PL")

    class Meta:
        model = Subscription


class SubmissionFactory(factory.django.DjangoModelFactory):
    newsletter = factory.SubFactory(NewsletterFactory)
    subscription = factory.SubFactory(SubscriptionFactory)
    message = factory.Faker("paragraph", nb_sentences=5)

    class Meta:
        model = Submission


factories_registry.register("newsletter", NewsletterFactory)
factories_registry.register("subscription", SubscriptionFactory)
factories_registry.register("submission", SubmissionFactory)
