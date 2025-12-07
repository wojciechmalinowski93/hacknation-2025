from django.db.models import Q
from django_tqdm import BaseCommand

from mcod.organizations.models import Organization


class Command(BaseCommand):
    def handle(self, *args, **options):
        for org in Organization.objects.filter(Q(title_en="") | Q(description_en="") | Q(slug_en="")).iterator():
            if org.title_en == "":
                org.title_en = None
                self.stdout.write(f"Organization(id={org.id}).title_en set to None")
            if org.description_en == "":
                org.description_en = None
                self.stdout.write(f"Organization(id={org.id}).description_en set to None")
            if org.slug_en == "":
                org.slug_en = None
                self.stdout.write(f"Organization(id={org.id}).slug_en set to None")
            org.save()
            self.stdout.write(f"Organization(id={org.id}) saved")
