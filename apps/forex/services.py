import logging
import requests
from decimal import Decimal
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

CACHE_TTL = int(getattr(settings, 'FOREX_CACHE_TTL', 300))


def get_live_rate(from_currency: str, to_currency: str) -> Decimal | None:
    """
    Recupere le taux de change en temps reel.
    Ordre de priorite : Cache Redis -> ECB (gratuit) -> ExchangeRate-API -> Fixer.io
    Retourne None si tous les providers echouent.
    """
    if from_currency == to_currency:
        return Decimal('1')

    cache_key = f"live_rate:{from_currency}:{to_currency}"
    cached = cache.get(cache_key)
    if cached:
        logger.debug(f"Cache hit pour {from_currency}/{to_currency}")
        return Decimal(cached)

    # DB first — rates are synced every 15 min by Celery, so this is fast
    # (~10ms) and fresh enough for API consumers.
    rate = _fetch_from_db(from_currency, to_currency)
    if rate is None:
        rate = (
            _fetch_ecb(from_currency, to_currency)
            or _fetch_exchangerate_api(from_currency, to_currency)
            or _fetch_fixer(from_currency, to_currency)
        )

    if rate:
        cache.set(cache_key, str(rate), timeout=CACHE_TTL)
        logger.info(f"Taux {from_currency}/{to_currency} = {rate} (mis en cache {CACHE_TTL}s)")

    return rate


def _fetch_ecb(from_currency, to_currency):
    try:
        r = requests.get(
            f"https://www.frankfurter.app/latest?from={from_currency}&to={to_currency}",
            timeout=3
        )
        r.raise_for_status()
        data = r.json()
        return Decimal(str(data['rates'][to_currency]))
    except Exception as e:
        logger.warning(f"ECB (frankfurter.app) echec pour {from_currency}/{to_currency}: {e}")
        return None


def _fetch_exchangerate_api(from_currency, to_currency):
    api_key = getattr(settings, 'EXCHANGERATE_API_KEY', '')
    if not api_key:
        try:
            r = requests.get(
                f"https://api.exchangerate-api.com/v4/latest/{from_currency}",
                timeout=3
            )
            r.raise_for_status()
            data = r.json()
            rate = data['rates'].get(to_currency)
            if rate:
                return Decimal(str(rate))
        except Exception as e:
            logger.warning(f"ExchangeRate-API (gratuit) echec: {e}")
        return None
    try:
        r = requests.get(
            f"https://v6.exchangerate-api.com/v6/{api_key}/pair/{from_currency}/{to_currency}",
            timeout=3
        )
        r.raise_for_status()
        data = r.json()
        if data.get('result') == 'success':
            return Decimal(str(data['conversion_rate']))
    except Exception as e:
        logger.warning(f"ExchangeRate-API (pro) echec: {e}")
    return None


def _fetch_fixer(from_currency, to_currency):
    api_key = getattr(settings, 'FIXER_API_KEY', '')
    if not api_key:
        return None
    try:
        r = requests.get(
            'https://api.apilayer.com/fixer/latest',
            headers={'apikey': api_key},
            params={'base': from_currency, 'symbols': to_currency},
            timeout=3
        )
        r.raise_for_status()
        data = r.json()
        if data.get('success') and to_currency in data.get('rates', {}):
            return Decimal(str(data['rates'][to_currency]))
    except Exception as e:
        logger.warning(f"Fixer.io echec: {e}")
    return None


def _fetch_from_db(from_currency, to_currency):
    """Resolve a pair from stored rates: direct, inverse, or cross-rate."""
    try:
        from apps.forex.models import ExchangeRate
    except Exception:
        return None

    # 1) Direct pair (e.g. EUR/USD stored by the sync task)
    try:
        rate = ExchangeRate.objects.get(
            from_currency_id=from_currency, to_currency_id=to_currency
        )
        return rate.market_rate
    except ExchangeRate.DoesNotExist:
        pass

    # 2) Inverse pair (USD/EUR = 1 / EUR/USD)
    try:
        inv = ExchangeRate.objects.get(
            from_currency_id=to_currency, to_currency_id=from_currency
        )
        if inv.market_rate:
            return Decimal(1) / inv.market_rate
    except (ExchangeRate.DoesNotExist, Exception):
        pass

    # 3) Cross-rate via a shared anchor (USD/GBP = EUR/GBP / EUR/USD)
    try:
        to_rate = ExchangeRate.objects.get(to_currency_id=to_currency)
        anchor = to_rate.from_currency_id
        from_rate = ExchangeRate.objects.get(
            from_currency_id=anchor, to_currency_id=from_currency
        )
        if from_rate.market_rate:
            return to_rate.market_rate / from_rate.market_rate
    except Exception:
        pass

    return None
