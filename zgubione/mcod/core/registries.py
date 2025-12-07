import warnings
from collections import OrderedDict, defaultdict

from django.apps import apps


class FactoriesRegistry:
    def __init__(self):
        self._factories = defaultdict(OrderedDict)

    def register(self, object_name, serializer_cls):
        if object_name:
            self._factories[object_name] = serializer_cls

    def get_factory(self, object_name):
        return self._factories.get(object_name)


class HistoryRegistry:
    def __init__(self):
        self._table_names = defaultdict(OrderedDict)

    def register(self, model):
        self._table_names[model._meta.db_table] = (
            model._meta.app_label,
            model._meta.model_name,
        )

    def get_params(self, table_name):
        return self._table_names.get(table_name)

    def get_table_names(self):
        return sorted(self._table_names.keys())


class SerializerRegistry:
    def __init__(self):
        self._serializers = defaultdict(OrderedDict)

    def register(self, serializer_cls):
        _name = serializer_cls.opts.model_name
        if _name:
            _app, _model = _name.split(".")
            model = apps.get_model(_app, _model)
            if model in self._serializers:
                warnings.warn(
                    f"Overriding existing registry serializer "
                    f"`{self._serializers[model]}` by `{serializer_cls}` for model `{model}`."
                )
            self._serializers[model] = serializer_cls

    def get_serializer(self, model):
        return self._serializers.get(model)

    def items(self):
        return self._serializers.items()


csv_serializers_registry = SerializerRegistry()
object_attrs_registry = SerializerRegistry()
rdf_serializers_registry = SerializerRegistry()

factories_registry = FactoriesRegistry()
history_registry = HistoryRegistry()
