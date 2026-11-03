import secrets
from decimal import Decimal
from django.utils.timezone import now
from django.db import transaction as db_transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.contrib.auth.models import User

from apps.api_gateway.models import APIClient
from apps.forex.models import ExchangeRate
from .models import Wallet, Transaction, Transfer

# Même règle que les conversions : abonnés payants au taux réel (0 %),
# tier gratuit avec spread.
SPREAD_MAP = {
    'free': (Decimal('0.025'), Decimal('0.005')),
    'standard': (Decimal('0'), Decimal('0')),
    'premium': (Decimal('0'), Decimal('0')),
    'partner': (Decimal('0'), Decimal('0')),
}


class WalletListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        wallets = Wallet.objects.filter(user=request.user, is_active=True).select_related('currency')
        data = [{
            'id': str(w.id),
            'currency': {'code': w.currency.code, 'name': w.currency.name, 'symbol': w.currency.symbol},
            'balance': str(w.balance),
            'reserved_balance': str(w.reserved_balance),
            'available_balance': str(w.available_balance),
            'is_active': w.is_active,
        } for w in wallets]
        return Response({'success': True, 'wallets': data})

    def post(self, request):
        currency_code = request.data.get('currency_code', '').upper()
        if not currency_code:
            return Response({'success': False, 'error': 'currency_code is required.',
                             'code': 'missing_params'}, status=400)

        from apps.core.models import Currency
        if not Currency.objects.filter(code=currency_code, is_active=True).exists():
            return Response({'success': False,
                             'error': f'Unknown or inactive currency: {currency_code}.',
                             'code': 'unknown_currency'}, status=400)

        wallet, created = Wallet.objects.get_or_create(
            user=request.user, currency_id=currency_code,
            defaults={'is_active': True}
        )
        if not created and not wallet.is_active:
            wallet.is_active = True
            wallet.save()
        return Response({'success': True, 'created': created, 'wallet': {
            'id': str(wallet.id), 'currency': currency_code,
            'balance': str(wallet.balance), 'is_active': wallet.is_active,
        }}, status=201 if created else 200)


class WalletTransactionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, currency_code):
        try:
            wallet = Wallet.objects.get(user=request.user, currency_id=currency_code.upper())
        except Wallet.DoesNotExist:
            return Response({'success': False,
                             'error': f'No {currency_code.upper()} wallet found.',
                             'code': 'wallet_not_found'}, status=404)

        txs = wallet.transactions.all()[:50]
        data = [{
            'id': str(t.id), 'type': t.transaction_type,
            'amount': str(t.amount), 'balance_after': str(t.balance_after),
            'status': t.status, 'reference': t.reference,
            'created_at': t.created_at.isoformat(),
        } for t in txs]
        return Response({'success': True, 'transactions': data})


class TransferCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        recipient_id = request.data.get('recipient_id')
        source_cur = request.data.get('source_currency', '').upper()
        dest_cur = request.data.get('destination_currency', '').upper()
        amount = request.data.get('amount')

        if not all([recipient_id, source_cur, dest_cur, amount]):
            return Response({'success': False,
                             'error': 'recipient_id, source_currency, destination_currency and amount are required.',
                             'code': 'missing_params'}, status=400)

        try:
            amount = Decimal(str(amount))
            if amount <= 0:
                raise ValueError
        except Exception:
            return Response({'success': False,
                             'error': 'amount must be a positive number.',
                             'code': 'invalid_amount'}, status=400)

        try:
            recipient = User.objects.get(pk=recipient_id)
        except User.DoesNotExist:
            return Response({'success': False,
                             'error': f'Recipient {recipient_id} not found.',
                             'code': 'recipient_not_found'}, status=404)

        if recipient.pk == request.user.pk:
            return Response({'success': False,
                             'error': 'Cannot transfer to yourself.',
                             'code': 'self_transfer'}, status=400)

        from apps.core.models import Currency
        unknown = [c for c in (source_cur, dest_cur)
                   if not Currency.objects.filter(code=c, is_active=True).exists()]
        if unknown:
            return Response(
                {'success': False,
                 'error': f'Unknown or inactive currency: {", ".join(unknown)}.',
                 'code': 'unknown_currency'},
                status=400
            )

        # Resolve the rate via the service layer — supports inverse and
        # cross-rates (e.g. USD→XAF), not only pairs stored directly.
        from apps.forex.services import get_live_rate
        market_rate = get_live_rate(source_cur, dest_cur)
        if market_rate is None:
            return Response({'success': False,
                             'error': f'Rate {source_cur}/{dest_cur} temporarily unavailable. Try again later.',
                             'code': 'rate_unavailable'}, status=503)

        # request.auth = la clé API réellement utilisée (bon tier même si
        # le user possède plusieurs clés). Fallback JWT : première clé active.
        api_client = request.auth if isinstance(request.auth, APIClient) else None
        if api_client is None:
            api_client = request.user.api_clients.filter(is_active=True).first()
        tier = api_client.tier if api_client else 'free'
        spread, margin = SPREAD_MAP.get(tier, SPREAD_MAP['standard'])
        applied_rate = market_rate * (1 - spread - margin)
        dest_amount = amount * applied_rate
        fee = amount * market_rate * (spread + margin)

        try:
            sender_wallet = Wallet.objects.get(user=request.user, currency_id=source_cur, is_active=True)
        except Wallet.DoesNotExist:
            return Response({'success': False,
                             'error': f'You do not have an active {source_cur} wallet. Create one via POST /api/v1/wallets/.',
                             'code': 'wallet_not_found'}, status=404)

        if sender_wallet.available_balance < amount:
            return Response({'success': False,
                             'error': f'Insufficient funds: available balance is {sender_wallet.available_balance} {source_cur}.',
                             'code': 'insufficient_funds',
                             'available_balance': str(sender_wallet.available_balance)}, status=422)

        recipient_wallet, _ = Wallet.objects.get_or_create(
            user=recipient, currency_id=dest_cur, defaults={'is_active': True}
        )

        reference = f"TXF{secrets.token_hex(5).upper()}"

        with db_transaction.atomic():
            sender_bal_before = sender_wallet.balance
            sender_wallet.balance -= amount
            sender_wallet.save()
            sender_tx = Transaction.objects.create(
                wallet=sender_wallet, transaction_type='debit', amount=amount,
                balance_before=sender_bal_before, balance_after=sender_wallet.balance,
                status='completed', reference=reference,
            )

            recip_bal_before = recipient_wallet.balance
            recipient_wallet.balance += dest_amount
            recipient_wallet.save()
            recip_tx = Transaction.objects.create(
                wallet=recipient_wallet, transaction_type='credit', amount=dest_amount,
                balance_before=recip_bal_before, balance_after=recipient_wallet.balance,
                status='completed', reference=reference,
            )

            transfer = Transfer.objects.create(
                reference=reference, sender=request.user, recipient=recipient,
                sender_wallet=sender_wallet, recipient_wallet=recipient_wallet,
                source_amount=amount, source_currency_id=source_cur,
                destination_amount=dest_amount, destination_currency_id=dest_cur,
                market_rate=market_rate, applied_rate=applied_rate,
                spread_pct=spread, fee_amount=fee, tier=tier,
                status='completed', sender_transaction=sender_tx,
                recipient_transaction=recip_tx, completed_at=now(),
            )

        return Response({'success': True, 'transfer': {
            'reference': transfer.reference,
            'source_amount': str(transfer.source_amount),
            'source_currency': source_cur,
            'destination_amount': str(round(dest_amount, 4)),
            'destination_currency': dest_cur,
            'market_rate': str(market_rate),
            'applied_rate': str(round(applied_rate, 8)),
            'spread_pct': str(spread),
            'fee_amount': str(round(fee, 4)),
            'status': transfer.status,
            'initiated_at': transfer.initiated_at.isoformat(),
            'completed_at': transfer.completed_at.isoformat(),
        }}, status=201)


class TransferListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        transfers = Transfer.objects.filter(sender=request.user).order_by('-initiated_at')[:50]
        data = [{
            'reference': t.reference, 'source_amount': str(t.source_amount),
            'source_currency': t.source_currency_id,
            'destination_amount': str(t.destination_amount),
            'destination_currency': t.destination_currency_id,
            'status': t.status, 'initiated_at': t.initiated_at.isoformat(),
        } for t in transfers]
        return Response({'success': True, 'transfers': data})


class TransferDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, reference):
        try:
            t = Transfer.objects.get(reference=reference, sender=request.user)
        except Transfer.DoesNotExist:
            return Response({'success': False,
                             'error': f'Transfer {reference} not found.',
                             'code': 'transfer_not_found'}, status=404)

        return Response({'success': True, 'transfer': {
            'reference': t.reference, 'source_amount': str(t.source_amount),
            'source_currency': t.source_currency_id,
            'destination_amount': str(t.destination_amount),
            'destination_currency': t.destination_currency_id,
            'market_rate': str(t.market_rate), 'applied_rate': str(t.applied_rate),
            'spread_pct': str(t.spread_pct), 'fee_amount': str(t.fee_amount),
            'tier': t.tier, 'status': t.status,
            'initiated_at': t.initiated_at.isoformat(),
            'completed_at': t.completed_at.isoformat() if t.completed_at else None,
        }})


class WalletCreditView(APIView):
    """Admin-only: credit a user's wallet (after receiving real funds)."""
    permission_classes = [IsAdminUser]

    def post(self, request):
        username = request.data.get('username', '').strip()
        currency_code = request.data.get('currency', '').upper()
        amount = request.data.get('amount')
        note = request.data.get('note', '')

        if not all([username, currency_code, amount]):
            return Response({'success': False,
                             'error': 'username, currency and amount are required.',
                             'code': 'missing_params'}, status=400)
        try:
            amount = Decimal(str(amount))
            if amount <= 0:
                raise ValueError
        except Exception:
            return Response({'success': False,
                             'error': 'amount must be a positive number.',
                             'code': 'invalid_amount'}, status=400)
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({'success': False,
                             'error': f'User {username} not found.',
                             'code': 'user_not_found'}, status=404)

        wallet, _ = Wallet.objects.get_or_create(
            user=user, currency_id=currency_code, defaults={'is_active': True}
        )
        reference = f"DEP{secrets.token_hex(5).upper()}"
        with db_transaction.atomic():
            before = wallet.balance
            wallet.balance += amount
            wallet.save()
            Transaction.objects.create(
                wallet=wallet, transaction_type='credit', amount=amount,
                balance_before=before, balance_after=wallet.balance,
                status='completed', reference=reference,
            )
        return Response({'success': True, 'reference': reference,
                         'new_balance': str(wallet.balance)})
