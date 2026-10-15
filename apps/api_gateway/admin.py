from django.contrib import admin, messages
from django.utils.html import format_html
from .models import APIClient, AuditLog, Subscription, Payment


def _badge(text, color):
    return format_html(
        '<span style="background:{c};color:#fff;padding:2px 8px;'
        'border-radius:10px;font-size:11px;">{t}</span>', c=color, t=text
    )


TIER_COLORS = {
    'free': '#6b7280', 'standard': '#2563eb',
    'premium': '#7c3aed', 'partner': '#b45309',
}
STATUS_COLORS = {
    'active': '#16a34a', 'pending': '#d97706', 'trial': '#0ea5e9',
    'cancelled': '#6b7280', 'expired': '#dc2626', 'failed': '#dc2626',
    'completed': '#16a34a', 'refunded': '#6b7280',
}


@admin.register(APIClient)
class APIClientAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'tier_badge', 'api_key_prefix',
                    'quota_requests_per_hour', 'total_requests',
                    'active_badge', 'created_at']
    list_filter = ['tier', 'is_active', 'created_at']
    search_fields = ['name', 'user__username', 'user__email', 'api_key_prefix']
    readonly_fields = ['api_key_prefix', 'api_key_hash', 'total_requests', 'created_at']
    list_select_related = ['user']
    date_hierarchy = 'created_at'
    actions = ['activate_clients', 'deactivate_clients']

    fieldsets = (
        ('Informations générales', {
            'fields': ('user', 'name', 'tier', 'is_active')
        }),
        ('Configuration API', {
            'fields': ('api_key_prefix', 'api_key_hash', 'quota_requests_per_hour'),
            'description': 'La clé complète n\'est jamais stockée — seul le hash '
                           'et le préfixe sont conservés.',
        }),
        ('Statistiques', {
            'fields': ('total_requests', 'created_at', 'expires_at')
        }),
    )

    def tier_badge(self, obj):
        return _badge(obj.tier.upper(), TIER_COLORS.get(obj.tier, '#6b7280'))
    tier_badge.short_description = 'Tier'

    def active_badge(self, obj):
        return _badge('ACTIF', '#16a34a') if obj.is_active else _badge('INACTIF', '#dc2626')
    active_badge.short_description = 'Statut'

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ['user']
        return self.readonly_fields

    @admin.action(description='Activer les clés API sélectionnées')
    def activate_clients(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} client(s) API activé(s).', messages.SUCCESS)

    @admin.action(description='Désactiver les clés API (bloque immédiatement leurs requêtes)')
    def deactivate_clients(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} client(s) API désactivé(s).', messages.WARNING)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'status_badge', 'start_date', 'end_date',
                    'auto_renew', 'is_active_badge']
    list_filter = ['plan', 'status', 'auto_renew', 'start_date']
    search_fields = ['user__username', 'user__email',
                     'stripe_customer_id', 'stripe_subscription_id']
    readonly_fields = ['start_date']
    date_hierarchy = 'start_date'

    fieldsets = (
        ('Informations abonnement', {
            'fields': ('user', 'plan', 'status', 'auto_renew')
        }),
        ('Dates', {
            'fields': ('start_date', 'end_date')
        }),
        ('Paiement Stripe', {
            'fields': ('stripe_customer_id', 'stripe_subscription_id'),
            'classes': ('collapse',),
        }),
    )

    def status_badge(self, obj):
        return _badge(obj.status.upper(), STATUS_COLORS.get(obj.status, '#6b7280'))
    status_badge.short_description = 'Statut'

    def is_active_badge(self, obj):
        if obj.is_active():
            return format_html('<span style="color:#16a34a;">✓ En cours</span>')
        return format_html('<span style="color:#dc2626;">✗ Terminé</span>')
    is_active_badge.short_description = 'Validité'

    actions = ['activate_subscriptions', 'cancel_subscriptions']

    @admin.action(description='Activer les abonnements sélectionnés')
    def activate_subscriptions(self, request, queryset):
        updated = queryset.update(status='active')
        self.message_user(request, f'{updated} abonnement(s) activé(s).', messages.SUCCESS)

    @admin.action(description='Annuler les abonnements sélectionnés')
    def cancel_subscriptions(self, request, queryset):
        updated = queryset.update(status='cancelled', auto_renew=False)
        self.message_user(request, f'{updated} abonnement(s) annulé(s).', messages.WARNING)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['user', 'subscription', 'amount', 'payment_method',
                    'status_badge', 'created_at']
    list_filter = ['payment_method', 'status', 'created_at']
    search_fields = ['user__username', 'user__email',
                     'transaction_id', 'stripe_payment_intent_id']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    list_select_related = ['user', 'subscription']

    fieldsets = (
        ('Informations paiement', {
            'fields': ('user', 'subscription', 'amount', 'currency',
                       'payment_method', 'status')
        }),
        ('Identifiants transaction', {
            'fields': ('transaction_id', 'stripe_payment_intent_id',
                       'paypal_order_id'),
            'classes': ('collapse',),
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',),
        }),
    )

    def status_badge(self, obj):
        return _badge(obj.status.upper(), STATUS_COLORS.get(obj.status, '#6b7280'))
    status_badge.short_description = 'Statut'

    actions = ['mark_as_completed', 'mark_as_failed']

    @admin.action(description='Valider comme payé (active l\'abonnement + met à jour la clé API)')
    def mark_as_completed(self, request, queryset):
        count = 0
        for payment in queryset:
            if payment.status == 'pending':
                payment.mark_completed()
                count += 1
        self.message_user(
            request,
            f'{count} paiement(s) validé(s). Abonnement activé et clé API mise à jour.',
            messages.SUCCESS,
        )

    @admin.action(description='Marquer comme échoué')
    def mark_as_failed(self, request, queryset):
        updated = queryset.filter(status='pending').update(status='failed')
        self.message_user(request, f'{updated} paiement(s) marqué(s) échoué(s).')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'user', 'api_client', 'method', 'path',
                    'status_badge', 'response_time_ms']
    list_filter = ['method', 'status_code', 'timestamp']
    search_fields = ['path', 'user__username', 'api_client__name']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'
    list_per_page = 50
    list_select_related = ['user', 'api_client']

    def status_badge(self, obj):
        code = obj.status_code or 0
        color = '#16a34a' if code < 300 else ('#d97706' if code < 500 else '#dc2626')
        return _badge(code, color)
    status_badge.short_description = 'HTTP'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
