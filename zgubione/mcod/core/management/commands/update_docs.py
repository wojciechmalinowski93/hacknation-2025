from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Regenerate API documentation"

    def handle(self, *args, **options):
        pass
