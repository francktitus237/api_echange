from django.contrib import admin, messages
from django.db import transaction as db_transaction
from django.utils.html import format_html
from .models import Wallet, Transaction, Transfer


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ['user', 'currency', 'balance', 'reserved_balance',
                    'available_balance', 'is_active', 'created_at']
    list_filter = ['is_active', 'currency']
    search_fields = ['user__username', 'currency_id']
    readonly_fields = ['created_at']

    fieldsets = (
        ('Propriétaire', {'fields': ('user', 'currency', 'is_active')}),
        ('Soldes', {'fields': ('balance', 'reserved_balance')}),
        ('Dates', {'fields': ('created_at',)}),
    )


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'wallet', 'transaction_type', 'amount',
                    'status', 'reference', 'balance_after']
    list_filter = ['transaction_type', 'status', 'created_at']
    search_fields = ['reference', 'wallet__user__username']
    readonly_fields = ['wallet', 'transaction_type', 'amount', 'balance_before',
                       'balance_after', 'reference', 'created_at']
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = ['reference', 'sender', 'recipient', 'source_display',
                    'destination_display', 'status_badge', 'fee_amount', 'initiated_at']
    list_filter = ['status', 'tier', 'initiated_at']
    search_fields = ['reference', 'sender__username', 'recipient__username']
    readonly_fields = ['reference', 'sender', 'recipient', 'sender_wallet',
                       'recipient_wallet', 'source_amount', 'destination_amount',
                       'market_rate', 'applied_rate', 'spread_pct', 'fee_amount',
                       'tier', 'sender_transaction', 'recipient_transaction',
                       'initiated_at', 'completed_at']
    date_hierarchy = 'initiated_at'
    actions = ['mark_failed_and_refund']

    def source_display(self, obj):
        return f"{obj.source_amount} {obj.source_currency_id}"
    source_display.short_description = 'Envoyé'

    def destination_display(self, obj):
        return f"{obj.destination_amount} {obj.destination_currency_id}"
    destination_display.short_description = 'Reçu'

    def status_badge(self, obj):
        colors = {'completed': 'green', 'failed': 'red', 'pending': 'orange',
                  'initiated': 'gray', 'processing': 'blue'}
        return format_html(
            '<span style="color: {};">● {}</span>',
            colors.get(obj.status, 'gray'), obj.get_status_display()
        )
    status_badge.short_description = 'Statut'

    def has_add_permission(self, request):
        return False

    @admin.action(description='Marquer échoué + rembourser l\'expéditeur')
    def mark_failed_and_refund(self, request, queryset):
        refunded = 0
        for t in queryset.filter(status__in=['initiated', 'pending', 'processing']):
            with db_transaction.atomic():
                wallet = t.sender_wallet
                wallet.balance += t.source_amount
                wallet.save(update_fields=['balance'])
                if t.sender_transaction:
                    t.sender_transaction.status = 'reversed'
                    t.sender_transaction.save(update_fields=['status'])
                t.status = 'failed'
                t.save(update_fields=['status'])
                refunded += 1
        self.message_user(
            request,
            f'{refunded} transfert(s) marqué(s) échoué(s) et remboursé(s).',
            messages.SUCCESS if refunded else messages.WARNING,
        )
