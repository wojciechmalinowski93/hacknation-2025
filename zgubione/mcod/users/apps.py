from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

from mcod.core.apps import ExtendedAppMixin


class UsersConfig(ExtendedAppMixin, AppConfig):
    name = "mcod.users"
    verbose_name = _("Users")

    def ready(self):
        from mcod.users.models import Meeting, MeetingTrash, User, UserFollowingDataset

        self.connect_core_signals(Meeting)
        self.connect_core_signals(MeetingTrash)
        self.connect_history(Meeting, User, UserFollowingDataset)
