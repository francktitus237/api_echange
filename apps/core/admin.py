from django.contrib import admin
from .models import Currency


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'symbol', 'flag', 'is_active']
    list_filter = ['is_active']
    search_fields = ['code', 'name']
    list_editable = ['is_active']
    ordering = ['code']


# ---------------------------------------------------------------------------
# Organisation du tableau de bord admin
# ---------------------------------------------------------------------------
admin.site.site_header = 'ForexPlatform — Administration'
admin.site.site_title = 'ForexPlatform Admin'
admin.site.index_title = 'Tableau de bord'
admin.site.site_url = '/api/docs/'

# Ordre d'affichage des sections et modèles sur la page d'accueil admin.
# Les apps/modèles non listés sont affichés après, par ordre alphabétique.
APP_ORDER = [
    'api_gateway',
    'transfers',
    'forex',
    'core',
    'auth',
    'django_celery_beat',
]

MODEL_ORDER = {
    'api_gateway': ['apiclient', 'payment', 'subscription', 'auditlog'],
    'transfers': ['wallet', 'transfer', 'transaction'],
    'forex': ['exchangerate', 'forexprovider', 'ratehistory'],
    'core': ['currency'],
    'auth': ['user', 'group'],
    'django_celery_beat': ['periodictask', 'intervalschedule', 'crontabschedule'],
}


def _ordered_app_list(request, app_label=None):
    app_list = admin.AdminSite.get_app_list(admin.site, request, app_label)
    app_list.sort(key=lambda a: (
        APP_ORDER.index(a['app_label']) if a['app_label'] in APP_ORDER else len(APP_ORDER),
        a['name'],
    ))
    for app in app_list:
        order = MODEL_ORDER.get(app['app_label'])
        if order:
            app['models'].sort(key=lambda m: (
                order.index(m['object_name'].lower()) if m['object_name'].lower() in order else len(order),
                m['name'],
            ))
    return app_list


admin.site.get_app_list = _ordered_app_list
