from django.contrib import admin
from .models import Currency


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'symbol', 'flag', 'is_active']
    list_filter = ['is_active']
    search_fields = ['code', 'name']
    list_editable = ['is_active']
    ordering = ['code']
