import logging

from django.core.management.base import BaseCommand

from mcod.discourse.manager import DiscourseManager

logger = logging.getLogger("mcod")


class Command(BaseCommand):

    def handle(self, *args, **options):
        manager = DiscourseManager()
        manager.sync_users()
