from decimal import Decimal
from django.utils.timezone import now
from django.core.cache import cache
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from apps.api_gateway.authentication import APIKeyAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.core.models import Currency
from .models import ExchangeRate, ForexProvider, RateHistory
from .services import get_live_rate

SPREAD_MAP = {
    'free': (Decimal('0.025'), Decimal('0.005')),
    'standard': (Decimal('0.015'), Decimal('0.003')),
    'premium': (Decimal('0.008'), Decimal('0.002')),
    'partner': (Decimal('0.003'), Decimal('0.001')),
}


class CurrencyListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        currencies = Currency.objects.filter(is_active=True).values('code', 'name', 'symbol', 'flag')
        return Response({'success': True, 'count': len(currencies), 'currencies': list(currencies)})


class RateListView(APIView):
    authentication_classes = [JWTAuthentication, APIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        base = request.query_params.get('base', 'USD').upper()
        cache_key = f"rates:{base}"
        cached = cache.get(cache_key)
        source = 'cache' if cached else 'db'

        if not cached:
            rates_qs = ExchangeRate.objects.filter(from_currency=base).select_related('to_currency')
            if not rates_qs.exists():
                return Response({'success': False, 'error': f'No rates found for base {base}.'}, status=404)
            cached = {
                r.to_currency_id: {
                    'market_rate': str(r.market_rate),
                    'business_rate': str(r.business_rate),
                    'spread': str(r.spread),
                    'fetched_at': r.fetched_at.isoformat(),
                    'is_stale': r.is_stale,
                } for r in rates_qs
            }
            cache.set(cache_key, cached, timeout=getattr(settings, 'FOREX_CACHE_TTL', 300))

        return Response({
            'success': True, 'source': source, 'base': base,
            'count': len(cached), 'timestamp': now().isoformat(), 'rates': cached
        })


class RatePairView(APIView):
    authentication_classes = [JWTAuthentication, APIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, from_currency, to_currency):
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()

        rate = get_live_rate(from_currency, to_currency)
        if rate is None:
            return Response({'success': False, 'error': f'Rate {from_currency}/{to_currency} not available.'}, status=404)

        return Response({'success': True, 'source': 'live', 'rate': {
            'pair': f"{from_currency}/{to_currency}",
            'from_currency': from_currency,
            'to_currency': to_currency,
            'market_rate': str(rate),
            'timestamp': now().isoformat(),
        }})


class ConvertView(APIView):
    authentication_classes = [JWTAuthentication, APIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from_cur = request.data.get('from_currency', '').upper()
        to_cur = request.data.get('to_currency', '').upper()
        amount = request.data.get('amount')

        api_client = request.user.api_clients.filter(is_active=True).first() if request.user.is_authenticated else None
        tier = api_client.tier if api_client else 'standard'

        if not all([from_cur, to_cur, amount]):
            return Response({'success': False, 'error': 'from_currency, to_currency and amount are required.'}, status=400)
        try:
            amount = Decimal(str(amount))
            if amount <= 0:
                raise ValueError
        except (ValueError, Exception):
            return Response({'success': False, 'error': 'amount must be a positive number.'}, status=400)

        market_rate = get_live_rate(from_cur, to_cur)
        if market_rate is None:
            return Response(
                {'success': False, 'error': f'Rate {from_cur}/{to_cur} temporarily unavailable. Try again later.'},
                status=503
            )

        spread, margin = SPREAD_MAP.get(tier, SPREAD_MAP['standard'])
        business_rate = market_rate * (1 + spread + margin)
        converted = amount * business_rate
        fee = amount * spread * business_rate

        return Response({'success': True, 'conversion': {
            'from_currency': from_cur, 'to_currency': to_cur,
            'amount': str(amount),
            'converted_amount': str(round(converted, 4)),
            'market_rate': str(market_rate),
            'business_rate': str(round(business_rate, 8)),
            'spread_pct': str(round(spread * 100, 2)),
            'fee_amount': str(round(fee, 4)),
            'tier': tier,
            'source': 'live',
            'timestamp': now().isoformat(),
        }})


class RateHistoryView(APIView):
    authentication_classes = [JWTAuthentication, APIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, from_currency, to_currency):
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()
        days = min(int(request.query_params.get('days', 30)), 365)

        history = RateHistory.objects.filter(
            from_currency=from_currency, to_currency=to_currency
        ).order_by('-date')[:days]

        data = [{
            'date': h.date.isoformat(),
            'open_rate': str(h.open_rate), 'high_rate': str(h.high_rate),
            'low_rate': str(h.low_rate), 'close_rate': str(h.close_rate),
            'avg_rate': str(h.avg_rate), 'data_points': h.data_points,
        } for h in history]

        return Response({
            'success': True, 'from_currency': from_currency,
            'to_currency': to_currency, 'count': len(data), 'history': data
        })


class ForexStatsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        last_rate = ExchangeRate.objects.order_by('-fetched_at').first()
        return Response({'success': True, 'stats': {
            'total_currencies': Currency.objects.filter(is_active=True).count(),
            'total_pairs': ExchangeRate.objects.count(),
            'active_providers': ForexProvider.objects.filter(is_active=True).count(),
            'last_sync': last_rate.fetched_at.isoformat() if last_rate else None,
            'stale_pairs': ExchangeRate.objects.filter(is_stale=True).count(),
        }})


class ForexProvidersView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        providers = ForexProvider.objects.all().values(
            'id', 'name', 'code', 'is_active', 'is_free',
            'weight', 'priority', 'success_count', 'error_count', 'last_sync_at'
        )
        return Response({'success': True, 'providers': list(providers)})


class ForexSyncView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        try:
            from apps.forex.tasks import sync_all_rates
            task = sync_all_rates.delay()
            return Response({'success': True, 'task_id': str(task.id)})
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=500)


class DemoRatesView(APIView):
    """Public sample of real rates for the landing page — no auth required."""
    permission_classes = [AllowAny]

    def get(self, request):
        rates = (
            ExchangeRate.objects
            .filter(is_stale=False)
            .select_related('from_currency', 'to_currency')
            .order_by('-fetched_at')[:10]
        )
        return Response({
            'success': True,
            'rates': [
                {
                    'pair': f"{r.from_currency.code}/{r.to_currency.code}",
                    'rate': str(round(r.market_rate, 6)),
                    'updated_at': r.fetched_at.isoformat(),
                    'stale': r.is_stale,
                }
                for r in rates
            ],
        })
