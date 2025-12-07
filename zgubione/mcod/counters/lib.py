import datetime

from django.apps import apps
from django.db.models import Sum
from django.db.transaction import atomic
from django_elasticsearch_dsl.registries import registry
from django_redis import get_redis_connection
from elasticsearch.helpers import bulk as streaming_bulk
from elasticsearch_dsl.connections import connections

from mcod import settings

VIEWS_COUNT_PREFIX = "views_count"
DOWNLOADS_COUNT_PREFIX = "downloads_count"


class Counter:

    def __init__(self):
        self.con = get_redis_connection()
        self.date_counter_labels = ["resources.Resource"]
        self.labels_es_actions = {label: [] for label in settings.COUNTED_MODELS}

    def _get_last_save(self, oper):
        return self.con.get(f"{oper}_last_save") or "0"

    def _clear_counters(self):
        for oper in (VIEWS_COUNT_PREFIX, DOWNLOADS_COUNT_PREFIX):
            last_save = self._get_last_save(oper)
            for label in settings.COUNTED_MODELS:
                for k in self.con.scan_iter(f"{oper}:{last_save}:{label}:*"):
                    self.con.delete(k)

    def incr_download_count(self, obj_id):
        last_save = self._get_last_save(DOWNLOADS_COUNT_PREFIX)
        key = f"{DOWNLOADS_COUNT_PREFIX}:{last_save}:resources.Resource:{obj_id}"
        self.con.incr(key)

    def incr_view_count(self, label, obj_id):
        last_save = self._get_last_save(VIEWS_COUNT_PREFIX)
        key = f"{VIEWS_COUNT_PREFIX}:{last_save}:{label}:{obj_id}"
        self.con.incr(key)

    @atomic
    def save_counters(self):
        """
        Tworzy lub uaktualnia liczniki w bazie danych i elasticsearch'u
        na podstawie wartości zapisanych w redis od ostatniej aktualizacji.

        Metoda powinna być wołana jako zadanie przez CRON.
        """
        resource_counter_model = {
            VIEWS_COUNT_PREFIX: apps.get_model("counters.ResourceViewCounter"),
            DOWNLOADS_COUNT_PREFIX: apps.get_model("counters.ResourceDownloadCounter"),
        }
        datasets_updates = {}
        today = datetime.date.today()
        for oper in (VIEWS_COUNT_PREFIX, DOWNLOADS_COUNT_PREFIX):
            last_save = self._get_last_save(oper)
            self.con.set(f"{oper}_last_save", str(int(datetime.datetime.now().timestamp())))

            for label, qs_params in settings.COUNTED_MODELS.items():
                model = apps.get_model(label)
                model.is_indexable = False
                data_key = f"{oper}:{last_save}:{label}:*"

                if label in self.date_counter_labels:
                    counter_model = resource_counter_model[oper]
                    self.save_resource_date_counters(oper, counter_model, data_key, label, model, today)

                for k in self.con.scan_iter(data_key):
                    obj_id = int(k.decode().split(":")[-1])
                    try:
                        obj = model.objects.get(pk=obj_id, **qs_params)
                    except model.DoesNotExist:
                        self.con.delete(k)
                        continue

                    incr_val = int(self.con.get(k))
                    counter = getattr(obj, oper) + incr_val
                    model.objects.filter(pk=obj_id, **qs_params).update(**{oper: counter})  # w/o send `save` signal.
                    self.add_es_action(model, obj, oper, counter, incr_val, datasets_updates)
                    self.con.delete(k)

        self.save_es_actions(datasets_updates)

    def save_resource_date_counters(self, oper, counter_model, data_key, label, model, today):
        view = label.split(".")[0]
        resources_to_update = {}
        for k in self.con.scan_iter(data_key):
            count_value = int(self.con.get(k))
            obj_id = int(k.decode().split(":")[-1])
            resources_to_update[obj_id] = count_value
            self.con.delete(k)
        existing_resources_to_update = list(
            model.objects.filter(pk__in=list(resources_to_update.keys()), status="published").values_list("pk", flat=True)
        )
        pub_resources_to_update = {
            published_res: resources_to_update[published_res] for published_res in existing_resources_to_update
        }
        existing_counters = counter_model.objects.filter(
            resource_id__in=existing_resources_to_update,
            timestamp=today,
            resource__status="published",
        )
        existing_counters_ids = set(list(existing_counters.values_list("resource_id", flat=True)))
        all_to_update = set(pub_resources_to_update.keys())
        no_count_resources = all_to_update.difference(existing_counters_ids)
        to_create_counters = []
        for resource_id in no_count_resources:
            to_create_counters.append(counter_model(count=pub_resources_to_update[resource_id], resource_id=resource_id))
        for current_counter in existing_counters:
            current_counter.count += pub_resources_to_update[current_counter.resource_id]
        counter_model.objects.bulk_create(to_create_counters)
        counter_model.objects.bulk_update(existing_counters, ["count"])
        annotation_label = "tmp_" + oper
        annotation = {annotation_label: Sum("count")}
        updated_counters = counter_model.objects.filter(resource_id__in=existing_resources_to_update)
        new_resource_counts = (
            updated_counters.values("resource_id").annotate(**annotation).values("resource_id", annotation_label)
        )
        new_dataset_counts = (
            updated_counters.values("resource__dataset_id")
            .annotate(**annotation)
            .values("resource__dataset_id", annotation_label)
        )
        es_oper_attr = f"computed_{oper}"
        for res in new_resource_counts:
            self.labels_es_actions["resources.Resource"].append(
                {
                    "_op_type": "update",
                    "_index": settings.ELASTICSEARCH_INDEX_NAMES[view],
                    "_type": "doc",
                    "_id": res["resource_id"],
                    "doc": {es_oper_attr: res[annotation_label]},
                }
            )
        for dataset in new_dataset_counts:
            try:
                self.labels_es_actions["datasets"].append(
                    {
                        "_op_type": "update",
                        "_index": settings.ELASTICSEARCH_INDEX_NAMES["datasets"],
                        "_type": "doc",
                        "_id": dataset["resource__dataset_id"],
                        "doc": {es_oper_attr: dataset[annotation_label]},
                    }
                )
            except KeyError:
                self.labels_es_actions["datasets"] = [
                    {
                        "_op_type": "update",
                        "_index": settings.ELASTICSEARCH_INDEX_NAMES["datasets"],
                        "_type": "doc",
                        "_id": dataset["resource__dataset_id"],
                        "doc": {es_oper_attr: dataset[annotation_label]},
                    }
                ]

    def save_es_actions(self, datasets_updates):
        dataset_model = apps.get_model("datasets.Dataset")
        for dataset_id, data in datasets_updates.items():
            dataset_model.objects.filter(pk=dataset_id).update(**data)
            if "datasets" not in self.labels_es_actions:
                self.labels_es_actions["datasets"] = []
            self.labels_es_actions["datasets"].append(
                {
                    "_op_type": "update",
                    "_index": settings.ELASTICSEARCH_INDEX_NAMES["datasets"],
                    "_type": "doc",
                    "_id": dataset_id,
                    "doc": data,
                }
            )
        es_actions = []
        for view_actions in self.labels_es_actions.values():
            es_actions.extend(view_actions)
        streaming_bulk(
            connections.get_connection(),
            es_actions,
            raise_on_error=False,
            raise_on_exception=False,
            max_retries=2,
        )

    def add_es_action(self, model, obj, oper, counter, incr_val, datasets_updates):
        document = next(iter(registry._models[model]))
        self.labels_es_actions[model._meta.label].append(
            {
                "_op_type": "update",
                "_type": "doc",
                "_index": document.Index.name,
                "_id": obj.pk,
                "doc": {oper: counter},
            }
        )
        try:
            if obj.dataset_id not in datasets_updates:
                datasets_updates[obj.dataset_id] = {}
            datasets_updates[obj.dataset_id].setdefault(oper, getattr(obj.dataset, oper))
            datasets_updates[obj.dataset_id][oper] += incr_val
        except AttributeError:
            pass
