from urllib import parse

import factory
from faker import Faker

from mcod.core.registries import factories_registry
from mcod.searchhistories import models as sh_models
from mcod.users.factories import UserFactory

fake = Faker("pl_PL")


class SearchHistoryFactory(factory.django.DjangoModelFactory):
    query_sentence = factory.Faker("text", max_nb_chars=100, locale="pl_PL")
    url = factory.LazyAttribute(lambda obj: f"http://test.dane.gov.pl/datasets?q={parse.quote(obj.query_sentence)}")
    user = factory.SubFactory(UserFactory)

    class Meta:
        model = sh_models.SearchHistory


factories_registry.register("search history", SearchHistoryFactory)
