from django.contrib import admin

from mcod.core.admin import LogEntryAdmin
from mcod.histories.models import LogEntry

admin.site.register(LogEntry, LogEntryAdmin)
