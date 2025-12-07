from django.contrib import admin
from django.shortcuts import redirect
from django.http import JsonResponse
from django.core.serializers.json import DjangoJSONEncoder
import json
from .models import Item

def export_selected_json(modeladmin, request, queryset):
    # Pobieramy dane z zaznaczonych wierszy
    data = list(queryset.values(
        'name', 'category', 'location_city', 
        'location_description', 'date_found', 'status'
    ))
    
    response = JsonResponse(
        data, 
        safe=False, 
        encoder=DjangoJSONEncoder,
        json_dumps_params={'ensure_ascii': False, 'indent': 4}
    )
    response['Content-Disposition'] = 'attachment; filename="zaznaczone_rzeczy.json"'
    return response

export_selected_json.short_description = "Pobierz JSON (zaznaczone)"

@admin.register(Item)
class LostItemAdmin(admin.ModelAdmin):
    list_display = ('name','status', 'created_at' ,'category', 'location_city', 'date_found')
    list_filter = ('category', 'date_found', 'location_city')
    search_fields = ('name', 'description', 'location_city')

    actions = [export_selected_json]

    # UKŁAD FORMULARZA 
    fieldsets = (
        ('Krok 1: Co znaleziono?', {
            'fields': ('name', 'category', 'image'),
            'description': 'Podstawowe informacje o przedmiocie.'
        }),
        ('Krok 2: Gdzie i kiedy?', {
            'fields': ('location_city', 'location_description', 'date_found'),
        }),
        ('Krok 3: Szczegóły i Kontakt', {
            'fields': ('description', 'contact_info', 'status'),
            'description': 'Gdzie obywatel może odebrać zgubę?'
        }),
    )

    icon_name = 'assignment'

    def response_add(self, request, obj, post_url_continue=None):
        return redirect('item_summary', item_id=obj.id)
