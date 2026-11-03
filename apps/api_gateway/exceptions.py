from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    """Uniformise les erreurs DRF (401/403/404/validation) au format
    {'success': False, 'error': <message lisible>, 'code': <code machine>}
    utilisé partout ailleurs dans l'API — une seule forme à parser côté client."""
    response = exception_handler(exc, context)
    if response is None:
        return None

    data = {'success': False}

    detail = response.data.get('detail') if isinstance(response.data, dict) else None
    if isinstance(detail, list):
        detail = '; '.join(str(d) for d in detail)
    if detail:
        data['error'] = str(detail)
        code = getattr(exc, 'default_code', None)
        if code:
            data['code'] = str(code)
    else:
        # Erreurs de validation (dict champ -> messages)
        data['error'] = 'Invalid request parameters.'
        data['errors'] = response.data
        data['code'] = 'validation_error'

    response.data = data
    return response
