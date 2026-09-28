from django.contrib import admin
from django.utils.html import format_html
from .models import APIClient, AuditLog, Subscription


@admin.register(APIClient)
class APIClientAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'tier', 'api_key_prefix', 'quota_requests_per_hour', 'total_requests', 'is_active', 'created_at']
    list_filter = ['tier', 'is_active', 'created_at']
    search_fields = ['name', 'user__username', 'api_key_prefix']
    readonly_fields = ['api_key_prefix', 'api_key_hash', 'total_requests', 'created_at']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('user', 'name', 'tier', 'is_active')
        }),
        ('Configuration API', {
            'fields': ('api_key_prefix', 'api_key_hash', 'quota_requests_per_hour')
        }),
        ('Statistiques', {
            'fields': ('total_requests', 'created_at', 'expires_at')
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return self.readonly_fields + ['user']
        return self.readonly_fields


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'status', 'start_date', 'end_date', 'auto_renew', 'is_active_badge']
    list_filter = ['plan', 'status', 'auto_renew', 'start_date']
    search_fields = ['user__username', 'stripe_customer_id', 'stripe_subscription_id']
    readonly_fields = ['start_date']
    
    fieldsets = (
        ('Informations abonnement', {
            'fields': ('user', 'plan', 'status', 'auto_renew')
        }),
        ('Dates', {
            'fields': ('start_date', 'end_date')
        }),
        ('Paiement Stripe', {
            'fields': ('stripe_customer_id', 'stripe_subscription_id')
        }),
    )
    
    def is_active_badge(self, obj):
        if obj.is_active():
            return format_html('<span style="color: green;">✓ Actif</span>')
        return format_html('<span style="color: red;">✗ Inactif</span>')
    is_active_badge.short_description = 'Statut'
    
    actions = ['activate_subscriptions', 'cancel_subscriptions']
    
    def activate_subscriptions(self, request, queryset):
        updated = queryset.update(status='active')
        self.message_user(request, f'{updated} abonnement(s) activé(s).')
    activate_subscriptions.short_description = 'Activer les abonnements sélectionnés'
    
    def cancel_subscriptions(self, request, queryset):
        updated = queryset.update(status='cancelled', auto_renew=False)
        self.message_user(request, f'{updated} abonnement(s) annulé(s).')
    cancel_subscriptions.short_description = 'Annuler les abonnements sélectionnés'


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'user', 'api_client', 'method', 'path', 'status_code', 'response_time_ms']
    list_filter = ['method', 'status_code', 'timestamp']
    search_fields = ['path', 'user__username', 'api_client__name']
    readonly_fields = ['timestamp']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
