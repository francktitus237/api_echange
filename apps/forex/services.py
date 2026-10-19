import logging
import requests
from decimal import Decimal
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

CACHE_TTL = int(getattr(settings, 'FOREX_CACHE_TTL', 300))


def get_live_rate_detail(from_currency: str, to_currency: str) -> dict | None:
    """
    Recupere le taux de change en temps reel avec ses metadonnees.
    Ordre de priorite : Cache Redis -> DB -> ECB (gratuit) -> ExchangeRate-API -> Fixer.io
    Retourne {'rate', 'source', 'fetched_at', 'is_stale'} ou None si tous
    les providers echouent. 'fetched_at' est un datetime ou None (taux live provider).
    """
    if from_currency == to_currency:
        return {'rate': Decimal('1'), 'source': 'identity', 'fetched_at': None, 'is_stale': False}

    cache_key = f"live_rate_detail:{from_currency}:{to_currency}"
    cached = cache.get(cache_key)
    if cached:
        logger.debug(f"Cache hit pour {from_currency}/{to_currency}")
        return {**cached, 'rate': Decimal(cached['rate'])}

    # DB first — rates are synced every 15 min by Celery, so this is fast
    # (~10ms) and fresh enough for API consumers.
    detail = _fetch_from_db_detail(from_currency, to_currency)
    if detail is None:
        for source, fetcher in (
            ('ecb', _fetch_ecb),
            ('exchangerate-api', _fetch_exchangerate_api),
            ('fixer', _fetch_fixer),
        ):
            rate = fetcher(from_currency, to_currency)
            if rate:
                detail = {'rate': rate, 'source': source, 'fetched_at': None, 'is_stale': False}
                break

    if detail:
        # Normalise fetched_at en ISO pour que le format soit identique
        # en sortie de cache et hors cache.
        if detail['fetched_at']:
            detail['fetched_at'] = detail['fetched_at'].isoformat()
        cache.set(cache_key, {**detail, 'rate': str(detail['rate'])}, timeout=CACHE_TTL)
        logger.info(f"Taux {from_currency}/{to_currency} = {detail['rate']} (mis en cache {CACHE_TTL}s)")

    return detail


def get_live_rate(from_currency: str, to_currency: str) -> Decimal | None:
    """Retourne uniquement le taux — voir get_live_rate_detail pour les metadonnees."""
    detail = get_live_rate_detail(from_currency, to_currency)
    return detail['rate'] if detail else None


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


def _fetch_from_db_detail(from_currency, to_currency):
    """Resolve a pair from stored rates: direct, inverse, or cross-rate.
    Retourne {'rate', 'source', 'fetched_at', 'is_stale'} ou None."""
    try:
        from apps.forex.models import ExchangeRate
    except Exception:
        return None

    # 1) Direct pair (e.g. EUR/USD stored by the sync task)
    try:
        rate = ExchangeRate.objects.get(
            from_currency_id=from_currency, to_currency_id=to_currency
        )
        return {
            'rate': rate.market_rate, 'source': 'db',
            'fetched_at': rate.fetched_at, 'is_stale': rate.is_stale,
        }
    except ExchangeRate.DoesNotExist:
        pass

    # 2) Inverse pair (USD/EUR = 1 / EUR/USD)
    try:
        inv = ExchangeRate.objects.get(
            from_currency_id=to_currency, to_currency_id=from_currency
        )
        if inv.market_rate:
            return {
                'rate': Decimal(1) / inv.market_rate, 'source': 'inverse',
                'fetched_at': inv.fetched_at, 'is_stale': inv.is_stale,
            }
    except (ExchangeRate.DoesNotExist, Exception):
        pass

    # 3) Cross-rate via a shared anchor (USD/GBP = EUR/GBP / EUR/USD)
    try:
        for to_rate in ExchangeRate.objects.filter(to_currency_id=to_currency):
            anchor = to_rate.from_currency_id
            from_rate = ExchangeRate.objects.filter(
                from_currency_id=anchor, to_currency_id=from_currency
            ).first()
            if from_rate and from_rate.market_rate and to_rate.market_rate:
                return {
                    'rate': to_rate.market_rate / from_rate.market_rate,
                    'source': 'cross',
                    'fetched_at': min(to_rate.fetched_at, from_rate.fetched_at),
                    'is_stale': to_rate.is_stale or from_rate.is_stale,
                }
    except Exception:
        pass

    return None
