from django.contrib import admin

from mcod.lib.admin_mixins import ModelAdmin
from mcod.searchhistories.models import SearchHistory


@admin.register(SearchHistory)
class SearchHistoryAdmin(ModelAdmin):
    list_display = ["id", "user_id", "query_sentence", "url"]
