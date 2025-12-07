from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from mcod import settings
from mcod.core.api.jsonapi.serializers import Object, object_attrs_registry as oar


class AdminMixin:

    @classmethod
    def get_admin_add_url(cls):
        return reverse(f"admin:{cls._meta.app_label}_{cls._meta.model_name}_add")

    @classmethod
    def get_admin_change_url(cls, obj_id, trash=""):
        return reverse(
            f"admin:{cls._meta.app_label}_{cls._meta.model_name}{trash}_change",
            args=(obj_id,),
        )

    @property
    def admin_change_url(self):
        return self.get_admin_change_url(self.id) if self.id else ""

    @property
    def admin_trash_change_url(self):
        return self.get_admin_change_url(self.id, "trash") if self.id else ""

    @classmethod
    def admin_list_url(cls):
        return reverse(f"admin:{cls._meta.app_label}_{cls._meta.model_name}_changelist")

    @classmethod
    def html_title_save(cls):
        return cls._html_title(_("Save"))

    @classmethod
    def html_title_save_and_continue(cls):
        return cls._html_title(_("Save and continue editing"))

    @classmethod
    def html_title_save_and_add_another(cls):
        return cls._html_title(_("Save and add another"))

    @classmethod
    def html_title_save_as_new(cls):
        return cls._html_title(_("Save as new"))

    @classmethod
    def html_title_close(cls):
        return cls._html_title(_("Close"))

    @classmethod
    def html_title_delete(cls):
        return cls._html_title(_("Delete"))

    @classmethod
    def _html_title(cls, type_):
        name = cls.accusative_case() if hasattr(cls, "accusative_case") else ""
        return f"{type_} {name}"

    def mark_safe(self, value):
        return mark_safe(value)

    def _reverse(self, *args, **kwargs):
        return reverse(*args, **kwargs)


class ApiMixin:

    @property
    def ident(self):
        return "{},{}".format(self.id, self.slug) if (hasattr(self, "slug") and self.slug) else self.id

    @property
    def api_url(self):
        return self.get_api_url()

    @property
    def api_url_base(self):
        return self._meta.app_label

    def get_api_url(self, base_url=settings.API_URL):
        if not self.id:
            return None

        return "{}/{}/{}".format(base_url, self.api_url_base, self.ident)

    def to_jsonapi(self, _schema=None, api_version=None):
        _schema = _schema or oar.get_serializer(self.__class__)
        data_cls = type("{}Data".format(self.__class__.__name__), (Object,), {})
        setattr(data_cls.opts, "attrs_schema", _schema)
        return data_cls(many=False, context={"api_version": api_version}).dump(self)

    @classmethod
    def _get_included(cls, ids, **kwargs):
        order_by = kwargs.pop("order_by", None)
        qs = cls.objects.filter(id__in=ids)
        return qs.order_by(*order_by) if isinstance(order_by, tuple) else qs

    @classmethod
    def get_included(cls, ids, **kwargs):
        api_version = kwargs.pop("api_version", None)
        return [x for x in (x.to_jsonapi(api_version=api_version) for x in cls._get_included(ids, **kwargs)) if x]


class IndexableMixin:
    @property
    def is_indexable(self):
        return True
