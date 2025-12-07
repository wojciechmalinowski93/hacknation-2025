from django.urls import path
from .views import item_summary, item_api_list

urlpatterns = [
    path('summary/<int:item_id>/', item_summary, name='item_summary'),
    path('api/v1/items/', item_api_list, name='item_api_list'),
]
