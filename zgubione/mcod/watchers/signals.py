from django.dispatch import Signal

model_watcher_updated = Signal(
    providing_args=[
        "instance",
        "obj_state",
        "prev_value",
    ]
)
query_watcher_updated = Signal(providing_args=["instance", "prev_value"])
query_watcher_created = Signal(providing_args=["instance", "created_at"])
