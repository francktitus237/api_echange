import logging
import requests
from celery import shared_task
from django.conf import settings
from django.utils.timezone import now

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def sync_all_rates(self):
    from apps.forex.models import ForexProvider, ExchangeRate
    from apps.core.models import Currency

    providers = ForexProvider.objects.filter(is_active=True).order_by('priority')
    all_rates = {}

    for provider in providers:
        try:
            rates = _fetch_provider(provider)
            if rates:
                for pair, rate in rates.items():
                    if pair not in all_rates:
                        all_rates[pair] = []
                    all_rates[pair].append((rate, provider.weight))
                provider.success_count += 1
                provider.last_sync_at = now()
                provider.save(update_fields=['success_count', 'last_sync_at'])
        except Exception as e:
            logger.error(f"Provider {provider.code} failed: {e}")
            provider.error_count += 1
            provider.save(update_fields=['error_count'])

    # Official fixed EUR pegs — treaty-fixed rates not published in eurofxref.
    # 1 EUR = 655.957 XAF/XOF (CFA francs), 491.9678 KMF (Comorian franc).
    PEGGED_EUR = {
        'XAF': 655.957,
        'XOF': 655.957,
        'KMF': 491.9678,
    }
    for code, peg in PEGGED_EUR.items():
        pair = f"EUR/{code}"
        if pair not in all_rates:
            all_rates[pair] = [(peg, 1.0)]

    spread = float(getattr(settings, 'FOREX_SPREAD_DEFAULT', 0.015))
    margin = float(getattr(settings, 'FOREX_MARGIN_DEFAULT', 0.005))
    updated = 0

    for pair, rate_list in all_rates.items():
        try:
            from_cur, to_cur = pair.split('/')
            total_weight = sum(w for _, w in rate_list)
            market_rate = sum(r * w for r, w in rate_list) / total_weight
            business_rate = market_rate * (1 + spread + margin)
            ExchangeRate.objects.update_or_create(
                from_currency_id=from_cur, to_currency_id=to_cur,
                defaults={
                    'market_rate': round(market_rate, 8),
                    'business_rate': round(business_rate, 8),
                    'spread': spread, 'margin': margin,
                    'is_stale': False,
                    'sources': [p[0] for p in rate_list],
                }
            )
            updated += 1
        except Exception as e:
            logger.error(f"Failed to update rate {pair}: {e}")

    logger.info(f"Sync complete. Updated {updated} pairs.")
    return updated


def _fetch_provider(provider):
    rates = {}
    try:
        if provider.code == 'openexchangerates':
            api_id = getattr(settings, 'OPENEXCHANGERATES_APP_ID', '')
            if not api_id:
                return {}
            r = requests.get(
                f"https://openexchangerates.org/api/latest.json?app_id={api_id}",
                timeout=10
            )
            data = r.json()
            if 'rates' in data:
                base = data.get('base', 'USD')
                for code, rate in data['rates'].items():
                    rates[f"{base}/{code}"] = rate

        elif provider.code == 'exchangerate_api':
            api_key = getattr(settings, 'EXCHANGERATE_API_KEY', '')
            if not api_key:
                return {}
            r = requests.get(
                f"https://v6.exchangerate-api.com/v6/{api_key}/latest/USD",
                timeout=10
            )
            data = r.json()
            if data.get('result') == 'success':
                for code, rate in data['conversion_rates'].items():
                    rates[f"USD/{code}"] = rate

        elif provider.code == 'ecb':
            r = requests.get(
                "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml",
                timeout=10
            )
            import xml.etree.ElementTree as ET
            root = ET.fromstring(r.content)
            ns = {'ecb': 'http://www.ecb.int/vocabulary/2002-08-01/eurofxref'}
            for cube in root.findall('.//ecb:Cube[@currency]', ns):
                code = cube.get('currency')
                rate = float(cube.get('rate', 0))
                if rate > 0:
                    rates[f"EUR/{code}"] = rate

    except Exception as e:
        logger.error(f"Fetch error for {provider.code}: {e}")

    return rates


@shared_task
def archive_daily_rates():
    from apps.forex.models import ExchangeRate, RateHistory
    from django.utils.timezone import now
    today = now().date()

    for rate in ExchangeRate.objects.all():
        RateHistory.objects.update_or_create(
            from_currency=rate.from_currency,
            to_currency=rate.to_currency,
            date=today,
            defaults={
                'open_rate': rate.market_rate,
                'high_rate': rate.market_rate,
                'low_rate': rate.market_rate,
                'close_rate': rate.market_rate,
                'avg_rate': rate.market_rate,
                'data_points': 1,
            }
        )
    logger.info(f"Daily rates archived for {today}")


@shared_task
def mark_stale_rates():
    from apps.forex.models import ExchangeRate
    from django.utils.timezone import now
    from datetime import timedelta
    threshold = now() - timedelta(hours=2)
    updated = ExchangeRate.objects.filter(fetched_at__lt=threshold, is_stale=False).update(is_stale=True)
    logger.info(f"Marked {updated} rates as stale.")
