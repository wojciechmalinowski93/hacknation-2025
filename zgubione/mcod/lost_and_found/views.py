from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from .models import Item

def item_summary(request, item_id):
    item = get_object_or_404(Item, pk=item_id)
    return render(request, 'lost_and_found/summary.html', {'item': item})

def item_api_list(request):
    items = Item.objects.filter(status__in=['lost', 'found']).values(
        'id', 'name', 'category', 'location_city', 
        'location_description', 'date_found', 'status'
    )
    
    data = list(items)
    
    return JsonResponse({
        'schema': 'Standard Rzeczy Znalezionych v1.0',
        'source': 'Dane.gov.pl Hackathon',
        'items': data
    }, safe=False, json_dumps_params={'ensure_ascii': False})
