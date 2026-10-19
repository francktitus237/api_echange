from django.core.cache import cache
from django.db.models import F
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import APIClient

# Le compteur total_requests est flushé en DB tous les N appels au lieu
# d'un UPDATE par requête (critique pour la conversion à chaque frappe).
REQUEST_COUNTER_FLUSH_EVERY = 100


class APIKeyAuthenticationScheme(OpenApiAuthenticationExtension):
    """Expose la clé API dans le schéma OpenAPI (bouton Authorize de Swagger UI)."""

    target_class = 'apps.api_gateway.authentication.APIKeyAuthentication'
    name = 'ApiKeyAuth'

    def get_security_definition(self, auto_schema):
        return {'type': 'apiKey', 'in': 'header', 'name': 'X-API-KEY'}


class APIKeyAuthentication(BaseAuthentication):
    """
    Authentification par clé API via le header X-API-KEY.
    Exemple : X-API-KEY: fxp_xxxxxxxxxxxxxxxx
    Utilisé par les apps mobiles et partenaires externes.
    """

    def authenticate(self, request):
        # Pas de ?api_key= en query param : les clés en URL finissent dans
        # les logs et l'historique — header uniquement.
        api_key = (
            request.META.get('HTTP_X_API_KEY')
            or request.META.get('HTTP_AUTHORIZATION', '').replace('ApiKey ', '', 1).strip()
        )
        if not api_key or not api_key.startswith('fxp_'):
            return None

        client = APIClient.verify_key(api_key)
        if not client:
            raise AuthenticationFailed('Invalid or inactive API key.')

        if client.expires_at:
            from django.utils.timezone import now
            if client.expires_at < now():
                raise AuthenticationFailed('API key expired.')

        self._count_request(client)

        # Expose the client on the underlying HttpRequest for AuditLogMiddleware
        request._request.api_client = client

        return (client.user, client)

    @staticmethod
    def _count_request(client):
        key = f"apiclient:reqcount:{client.pk}"
        try:
            if cache.add(key, 0, timeout=None):
                pass
            count = cache.incr(key)
            if count >= REQUEST_COUNTER_FLUSH_EVERY:
                APIClient.objects.filter(pk=client.pk).update(
                    total_requests=F('total_requests') + count
                )
                cache.delete(key)
        except Exception:
            # Le compteur ne doit jamais faire échouer la requête.
            pass

    def authenticate_header(self, request):
        return 'X-API-KEY'
