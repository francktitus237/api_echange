from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import APIClient


class APIKeyAuthentication(BaseAuthentication):
    """
    Authentification par clé API via le header X-API-KEY.
    Exemple : X-API-KEY: fxp_xxxxxxxxxxxxxxxx
    Utilisé par les apps mobiles et partenaires externes.
    """

    def authenticate(self, request):
        api_key = (
            request.META.get('HTTP_X_API_KEY')
            or request.META.get('HTTP_AUTHORIZATION', '').replace('ApiKey ', '', 1).strip()
            or request.query_params.get('api_key')
        )
        if not api_key or not api_key.startswith('fxp_'):
            return None

        client = APIClient.verify_key(api_key)
        if not client:
            raise AuthenticationFailed('Clé API invalide ou expirée.')

        if client.expires_at:
            from django.utils.timezone import now
            if client.expires_at < now():
                raise AuthenticationFailed('Clé API expirée.')

        client.total_requests += 1
        client.save(update_fields=['total_requests'])

        # Expose the client on the underlying HttpRequest for AuditLogMiddleware
        request._request.api_client = client

        return (client.user, client)

    def authenticate_header(self, request):
        return 'X-API-KEY'
