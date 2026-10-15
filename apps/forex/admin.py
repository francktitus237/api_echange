from django.contrib import admin, messages
from django.utils.html import format_html
from django.utils.timezone import now
from datetime import timedelta
from .models import ForexProvider, ExchangeRate, RateHistory


@admin.register(ForexProvider)
class ForexProviderAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_active', 'priority', 'weight',
                    'success_count', 'error_count', 'last_sync_at', 'health_badge']
    list_filter = ['is_active', 'is_free']
    list_editable = ['is_active', 'priority', 'weight']
    ordering = ['priority']
    actions = ['sync_now']

    def health_badge(self, obj):
        total = obj.success_count + obj.error_count
        if total == 0:
            return format_html('<span style="color: gray;">— jamais exécuté</span>')
        rate = obj.success_count / total
        color = 'green' if rate > 0.9 else ('orange' if rate > 0.5 else 'red')
        return format_html(
            '<span style="color: {};">{:.0f}% succès</span>', color, rate * 100
        )
    health_badge.short_description = 'Fiabilité'

    def sync_now(self, request, queryset):
        try:
            from apps.forex.tasks import sync_all_rates
            try:
                sync_all_rates.delay()
            except Exception:
                sync_all_rates()
            self.message_user(request, 'Synchronisation des taux lancée.', messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f'Échec de la synchronisation : {e}', messages.ERROR)
    sync_now.short_description = 'Synchroniser les taux maintenant'


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ['pair', 'market_rate', 'business_rate', 'spread',
                    'fetched_at', 'freshness_badge', 'is_stale']
    list_filter = ['is_stale', 'fetched_at']
    search_fields = ['from_currency_id', 'to_currency_id']
    readonly_fields = ['fetched_at']
    ordering = ['from_currency_id', 'to_currency_id']
    actions = ['mark_as_stale', 'mark_as_fresh']

    def pair(self, obj):
        return f"{obj.from_currency_id}/{obj.to_currency_id}"
    pair.short_description = 'Paire'

    def freshness_badge(self, obj):
        age = now() - obj.fetched_at
        if age < timedelta(hours=1):
            return format_html('<span style="color: green;">● Frais</span>')
        elif age < timedelta(hours=6):
            return format_html('<span style="color: orange;">● Ancien</span>')
        return format_html('<span style="color: red;">● Périmé</span>')
    freshness_badge.short_description = 'Fraîcheur'

    def mark_as_stale(self, request, queryset):
        updated = queryset.update(is_stale=True)
        self.message_user(request, f'{updated} paire(s) marquée(s) périmée(s).')
    mark_as_stale.short_description = 'Marquer comme périmé'

    def mark_as_fresh(self, request, queryset):
        updated = queryset.update(is_stale=False)
        self.message_user(request, f'{updated} paire(s) marquée(s) fraîche(s).')
    mark_as_fresh.short_description = 'Marquer comme frais'


@admin.register(RateHistory)
class RateHistoryAdmin(admin.ModelAdmin):
    list_display = ['pair', 'date', 'open_rate', 'high_rate', 'low_rate', 'close_rate', 'data_points']
    list_filter = ['date']
    search_fields = ['from_currency_id', 'to_currency_id']
    ordering = ['-date']
    date_hierarchy = 'date'

    def pair(self, obj):
        return f"{obj.from_currency_id}/{obj.to_currency_id}"
    pair.short_description = 'Paire'

    def has_add_permission(self, request):
        return False
