import time
from django.utils.timezone import now
from django.http import JsonResponse


class AuditLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.time()
        response = self.get_response(request)
        elapsed_ms = int((time.time() - start) * 1000)

        if request.path.startswith('/api/'):
            try:
                from .models import AuditLog
                user = request.user if request.user.is_authenticated else None
                api_client = getattr(request, 'api_client', None)
                ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
                if ',' in ip:
                    ip = ip.split(',')[0].strip()
                AuditLog.objects.create(
                    user=user,
                    api_client=api_client,
                    method=request.method,
                    path=request.path,
                    status_code=response.status_code,
                    ip_address=ip or None,
                    response_time_ms=elapsed_ms,
                )
            except Exception:
                pass
        return response


class RateLimitMiddleware:
    TIER_LIMITS = {
        'free': 100,
        'standard': 1000,
        'premium': 5000,
        'partner': 50000,
        'anonymous': 20,
    }

    def __init__(self, get_response):
        self.get_response = get_response

    EXEMPT_PATHS = ('/api/v1/health/', '/api/docs/', '/api/schema/', '/api/redoc/')

    def __call__(self, request):
        if request.path.startswith('/api/') and request.path not in self.EXEMPT_PATHS:
            try:
                from django.core.cache import cache
                from .models import APIClient

                # DRF auth runs inside the view — too late for middleware.
                # Resolve the X-API-KEY header ourselves so keyed clients get
                # their tier quota instead of the anonymous 20/hour bucket.
                api_client = getattr(request, 'api_client', None)
                raw_key = request.META.get('HTTP_X_API_KEY')
                if api_client is None and raw_key:
                    api_client = APIClient.verify_key(raw_key)
                if api_client is None and request.user.is_authenticated:
                    api_client = request.user.api_clients.filter(is_active=True).first()

                if api_client:
                    limit = api_client.quota_requests_per_hour or self.TIER_LIMITS.get(api_client.tier, 100)
                    key = f"ratelimit:client:{api_client.id}"
                else:
                    ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', 'unknown'))
                    if ',' in ip:
                        ip = ip.split(',')[0].strip()
                    key = f"ratelimit:{ip}"
                    limit = self.TIER_LIMITS['anonymous']

                count = cache.get(key, 0)
                if count >= limit:
                    return JsonResponse(
                        {'success': False, 'error': 'Rate limit exceeded. Try again later.'},
                        status=429
                    )
                cache.set(key, count + 1, timeout=3600)
            except Exception:
                pass
        return self.get_response(request)
