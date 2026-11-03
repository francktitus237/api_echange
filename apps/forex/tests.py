from decimal import Decimal

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase, override_settings

from apps.api_gateway.models import APIClient, AuditLog
from apps.core.models import Currency
from .models import ExchangeRate


class ConvertViewTests(TestCase):
    """Conversion temps réel appelée à chaque frappe par les apps clientes."""

    def setUp(self):
        cache.clear()
        Currency.objects.create(code='EUR', name='Euro', symbol='€')
        Currency.objects.create(code='USD', name='US Dollar', symbol='$')
        ExchangeRate.objects.create(
            from_currency_id='EUR', to_currency_id='USD',
            market_rate=Decimal('1.10'), business_rate=Decimal('1.10'),
        )
        self.user = User.objects.create_user(username='fintech', password='x')
        self.raw_key, key_hash, prefix = APIClient.generate_key()
        self.client_obj = APIClient.objects.create(
            user=self.user, name='Fintech App', api_key_prefix=prefix,
            api_key_hash=key_hash, tier='standard', quota_requests_per_hour=1000,
        )

    def _convert(self, **params):
        params.setdefault('from_currency', 'EUR')
        params.setdefault('to_currency', 'USD')
        return self.client.get('/api/v1/convert/', params, HTTP_X_API_KEY=self.raw_key)

    def test_convert_success(self):
        resp = self._convert(amount='100')
        self.assertEqual(resp.status_code, 200)
        conv = resp.json()['conversion']
        self.assertEqual(conv['converted_amount'], '110.0000')
        self.assertEqual(conv['market_rate'], '1.10000000')
        self.assertEqual(conv['tier'], 'standard')
        self.assertTrue(conv['estimated'])
        self.assertEqual(conv['rate_source'], 'db')
        self.assertIn('X-RateLimit-Limit', resp)

    def test_convert_zero_amount_graceful(self):
        """Champ remis à zéro pendant la saisie : succès, pas d'erreur 400."""
        resp = self._convert(amount='0')
        self.assertEqual(resp.status_code, 200)
        conv = resp.json()['conversion']
        self.assertEqual(conv['converted_amount'], '0')
        self.assertEqual(conv['market_rate'], '1.10000000')

    def test_convert_missing_params(self):
        resp = self._convert(amount='')
        self.assertEqual(resp.status_code, 400)

    def test_convert_invalid_amount(self):
        for bad in ('abc', '-5'):
            resp = self._convert(amount=bad)
            self.assertEqual(resp.status_code, 400, bad)

    def test_convert_requires_auth(self):
        resp = self.client.get('/api/v1/convert/', {
            'from_currency': 'EUR', 'to_currency': 'USD', 'amount': '10',
        })
        self.assertIn(resp.status_code, (401, 403))

    def test_rate_unavailable_returns_none(self):
        """Paire inconnue hors DB → detail None (la vue répondrait 503).
        Testé au niveau service : une réponse 503 en test plante le handler
        de logging Django (rendu page debug, bug de copie sous Python 3.14)."""
        from unittest.mock import patch
        from .services import get_live_rate_detail
        with patch('apps.forex.services._fetch_ecb', return_value=None), \
             patch('apps.forex.services._fetch_exchangerate_api', return_value=None), \
             patch('apps.forex.services._fetch_fixer', return_value=None):
            self.assertIsNone(get_live_rate_detail('USD', 'XXX'))

    def test_tier_uses_authenticated_key_not_first(self):
        """Un user avec plusieurs clés : le tier vient de la clé utilisée."""
        raw_key2, key_hash2, prefix2 = APIClient.generate_key()
        APIClient.objects.create(
            user=self.user, name='Premium key', api_key_prefix=prefix2,
            api_key_hash=key_hash2, tier='premium', quota_requests_per_hour=5000,
        )
        # La clé standard a été créée en premier : first() la renverrait,
        # mais l'auth par raw_key2 doit donner 'premium'.
        resp = self.client.get('/api/v1/convert/', {
            'from_currency': 'EUR', 'to_currency': 'USD', 'amount': '10',
        }, HTTP_X_API_KEY=raw_key2)
        self.assertEqual(resp.json()['conversion']['tier'], 'premium')

    def test_convert_uses_realtime_bucket_not_hourly_quota(self):
        for _ in range(3):
            self.assertEqual(self._convert(amount='1').status_code, 200)
        # Le quota horaire n'est pas consommé ; le bucket /min l'est.
        self.assertIsNone(cache.get(f"ratelimit:client:{self.client_obj.id}"))
        self.assertEqual(cache.get(f"ratelimit:rt:client:{self.client_obj.id}"), 3)

    @override_settings(FOREX_REALTIME_RATE_LIMIT=2)
    def test_realtime_burst_limit(self):
        self.assertEqual(self._convert(amount='1').status_code, 200)
        self.assertEqual(self._convert(amount='1').status_code, 200)
        resp = self._convert(amount='1')
        self.assertEqual(resp.status_code, 429)
        self.assertEqual(resp['Retry-After'], '60')

    def test_convert_not_audit_logged(self):
        self._convert(amount='5')
        self.assertFalse(AuditLog.objects.filter(path='/api/v1/convert/').exists())

    def test_request_counter_batched(self):
        """Pas d'UPDATE total_requests à chaque appel — flush tous les 100."""
        self._convert(amount='1')
        self.client_obj.refresh_from_db()
        self.assertEqual(self.client_obj.total_requests, 0)
        self.assertEqual(cache.get(f"apiclient:reqcount:{self.client_obj.pk}"), 1)
