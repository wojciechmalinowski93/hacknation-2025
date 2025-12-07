from django.dispatch import Signal, dispatcher


class ExtendedSignal(Signal):
    def __init__(self, providing_args=None, use_caching=False):
        if providing_args is None:
            providing_args = []
        providing_args.append("instance")
        providing_args.append("state")
        super().__init__(providing_args=providing_args, use_caching=use_caching)

    def send(self, sender, instance, *args, **named):
        if not self.receivers or self.sender_receivers_cache.get(sender) is dispatcher.NO_RECEIVERS:
            return []

        return [(receiver, receiver(sender, instance, *args, signal=self, **named)) for receiver in self._live_receivers(sender)]

    def send_robust(self, sender, instance, *args, **named):
        if not self.receivers or self.sender_receivers_cache.get(sender) is dispatcher.NO_RECEIVERS:
            return []

        responses = []
        for receiver in self._live_receivers(sender):
            try:
                response = receiver(sender, instance, *args, signal=self, **named)
            except Exception as err:
                responses.append((receiver, err))
            else:
                responses.append((receiver, response))
        return responses


notify_published = ExtendedSignal()
notify_updated = ExtendedSignal()
notify_restored = ExtendedSignal()
notify_removed = ExtendedSignal()

notify_m2m_added = ExtendedSignal()
notify_m2m_removed = ExtendedSignal()
notify_m2m_cleaned = ExtendedSignal()

permanently_remove_related_objects = ExtendedSignal()
