from django.utils.translation import gettext_lazy as _

SOURCE_TYPE_CHOICES = (("ckan", "CKAN"), ("xml", "XML"), ("dcat", "DCAT-AP"))
SOURCE_TYPE_CHOICES_FOR_ADMIN = dict(((None, _("Manually")), *SOURCE_TYPE_CHOICES))
