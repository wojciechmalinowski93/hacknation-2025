from django.apps import AppConfig

from mcod.core.apps import ExtendedAppMixin


class WatchersConfig(ExtendedAppMixin, AppConfig):
    name = "mcod.watchers"

    def ready(self):
        from mcod.watchers.models import Notification, Subscription, Watcher

        self.connect_history(Notification, Subscription, Watcher)
