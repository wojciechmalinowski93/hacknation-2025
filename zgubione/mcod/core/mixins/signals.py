import logging

signal_logger = logging.getLogger("signals")


class SignalLoggerMixin:

    def debug(self, message, sender, instance, signal_name):
        signal_logger.debug(
            message,
            extra={
                "sender": "{}.{}".format(sender._meta.model_name, sender._meta.object_name),
                "instance": "{}.{}".format(instance._meta.model_name, instance._meta.object_name),
                "instance_id": instance.id,
                "signal": signal_name,
            },
            exc_info=1,
        )
