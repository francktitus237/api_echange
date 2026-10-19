import time
from django.utils.timezone import now
from django.http import JsonResponse

# Endpoints "temps réel" appelés à chaque frappe (saisie du montant →
# conversion affichée sur l'autre écran). Ils ont une limite par minute
# dédiée et sont exclus du quota horaire.
REALTIME_PREFIXES = ('/api/v1/convert', '/api/v1/rates')


class AuditLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.time()
        response = self.get_response(request)
        elapsed_ms = int((time.time() - start) * 1000)

        # Endpoints temps réel (saisie par frappe) : un INSERT AuditLog par
        # appel ferait exploser la table sans valeur métier — l'usage reste
        # compté via total_requests.
        skip_audit = request.method in ('GET', 'POST') and request.path.startswith(REALTIME_PREFIXES)
        if request.path.startswith('/api/') and not skip_audit:
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
        'user': 500,        # JWT authentifié sans clé API
        'anonymous': 20,
    }

    def __init__(self, get_response):
        self.get_response = get_response

    EXEMPT_PATHS = ('/api/v1/health/', '/api/docs/', '/api/schema/', '/api/redoc/',
                    '/api/v1/docs/', '/api/v1/webhooks/stripe/')

    def __call__(self, request):
        if not request.path.startswith('/api/') or request.path in self.EXEMPT_PATHS:
            return self.get_response(request)
        try:
            from django.conf import settings
            from django.core.cache import cache
            from .models import APIClient

            # DRF auth runs inside the view — too late for middleware.
            # Resolve the X-API-KEY header ourselves so keyed clients get
            # their tier quota instead of the anonymous 20/hour bucket.
            api_client = getattr(request, 'api_client', None)
            raw_key = request.META.get('HTTP_X_API_KEY')
            if api_client is None and raw_key:
                api_client = APIClient.verify_key(raw_key)

            # JWT (Bearer) : request.user n'est PAS peuplé ici — l'auth DRF
            # tourne dans la vue. Sans ça, les clients JWT tombaient tous dans
            # le bucket anonyme par IP (20/h partagés entre utilisateurs).
            # On valide juste la signature du token pour bucketiser par user.
            user_id = None
            if api_client is None:
                auth_header = request.META.get('HTTP_AUTHORIZATION', '')
                if auth_header.startswith('Bearer '):
                    try:
                        from rest_framework_simplejwt.authentication import JWTAuthentication
                        token = JWTAuthentication().get_validated_token(auth_header[7:])
                        user_id = token.get('user_id')
                    except Exception:
                        user_id = None
                if user_id is None and request.user.is_authenticated:
                    user_id = request.user.pk
                if user_id:
                    api_client = self._client_for_user(user_id)

            ident = (f"client:{api_client.id}" if api_client
                     else f"user:{user_id}" if user_id
                     else f"ip:{self._ip(request)}")

            if request.path.startswith(REALTIME_PREFIXES):
                # Fenêtre d'une minute pour absorber la saisie par frappe ;
                # n'entame pas le quota horaire du client.
                limit = getattr(settings, 'FOREX_REALTIME_RATE_LIMIT', 300)
                window = 60
                key = f"ratelimit:rt:{ident}"
            else:
                if api_client:
                    quota = api_client.quota_requests_per_hour
                    if quota == 0:
                        # 0 = client illimité (partenaire interne) — aucun rate-limit.
                        return self.get_response(request)
                    limit = quota or self.TIER_LIMITS.get(api_client.tier, 100)
                else:
                    limit = self.TIER_LIMITS['user' if user_id else 'anonymous']
                window = 3600
                key = f"ratelimit:{ident}"

            # Fenêtre fixe : la clé expire une fois par fenêtre (l'ancien code
            # faisait cache.set à chaque appel, ce qui repoussait l'expiration
            # indéfiniment tant que le client restait actif).
            if cache.add(key, 1, timeout=window):
                count = 1
            else:
                try:
                    count = cache.incr(key)
                except ValueError:
                    cache.set(key, 1, timeout=window)
                    count = 1

            if count > limit:
                response = JsonResponse(
                    {'success': False,
                     'error': f'Rate limit exceeded: {limit} requests per {window}s. Retry after the window resets.',
                     'code': 'rate_limited'},
                    status=429
                )
                response['Retry-After'] = str(window)
                response['X-RateLimit-Remaining'] = '0'
                return response

            response = self.get_response(request)
            response['X-RateLimit-Limit'] = str(limit)
            response['X-RateLimit-Remaining'] = str(max(0, limit - count))
            return response
        except Exception:
            return self.get_response(request)

    @staticmethod
    def _ip(request):
        ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', 'unknown'))
        return ip.split(',')[0].strip() if ',' in ip else ip

    @staticmethod
    def _client_for_user(user_id):
        """Première clé active du user JWT (cache 60s — un lookup par requête
        sinon). Donne au user le quota de son tier réel."""
        from django.core.cache import cache
        from .models import APIClient
        key = f"apiclient:byuser:{user_id}"
        cached = cache.get(key)
        if cached is not None:
            return cached or None
        client = APIClient.objects.filter(user_id=user_id, is_active=True).order_by('id').first()
        cache.set(key, client or False, timeout=60)
        return client
