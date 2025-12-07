import factory

from mcod.core.registries import factories_registry
from mcod.organizations.models import Organization
from mcod.resources.dga_constants import ALLOWED_INSTITUTIONS_TO_USE_HIGH_VALUE_DATA_FROM_EC_LIST

_INSTITUTION_TYPES = [i[0] for i in Organization.INSTITUTION_TYPE_CHOICES]

# TODO remove the line below after restoring the functionality - creating an ES table index for Developers' resources
_INSTITUTION_TYPES = [i_type for i_type in _INSTITUTION_TYPES if i_type != Organization.INSTITUTION_TYPE_DEVELOPER]


class OrganizationFactory(factory.django.DjangoModelFactory):
    title = factory.Faker("company", locale="pl_PL")
    description = factory.Faker("paragraph", nb_sentences=5)
    email = factory.Faker("company_email")
    slug = factory.Faker("slug")
    abbreviation = "ABC"
    image = factory.django.ImageField(color="blue")
    institution_type = factory.Faker("random_element", elements=_INSTITUTION_TYPES)
    postal_code = factory.Faker("postcode", locale="pl_PL")
    city = factory.Faker("city", locale="pl_PL")
    street_type = factory.Faker("street_prefix_short", locale="pl_PL")
    street = factory.Faker("street_name", locale="pl_PL")
    street_number = factory.Faker("building_number", locale="pl_PL")
    email = factory.Faker("email", locale="pl_PL")
    epuap = factory.Faker("uri", locale="pl_PL")
    fax = factory.Faker("phone_number", locale="pl_PL")
    tel = factory.Faker("phone_number", locale="pl_PL")
    regon = factory.Faker("regon", locale="pl_PL")
    website = factory.Faker("url", locale="pl_PL")

    @factory.post_generation
    def users(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for user in extracted:
                self.users.add(user)

    class Meta:
        model = Organization
        django_get_or_create = ("title",)


class HvdEcOrganizationFactory(OrganizationFactory):
    institution_type = factory.Faker("random_element", elements=ALLOWED_INSTITUTIONS_TO_USE_HIGH_VALUE_DATA_FROM_EC_LIST)


class StateOrganizationFactory(OrganizationFactory):
    institution_type = Organization.INSTITUTION_TYPE_STATE


class PrivateOrganizationFactory(OrganizationFactory):
    institution_type = Organization.INSTITUTION_TYPE_PRIVATE


factories_registry.register("institution", OrganizationFactory)
factories_registry.register("hvd_institution", HvdEcOrganizationFactory)
