from django.urls import path
from . import views

urlpatterns = [
    path('demo/', views.DemoRatesView.as_view(), name='demo_rates'),
    path('currencies/', views.CurrencyListView.as_view(), name='currencies'),
    path('rates/', views.RateListView.as_view(), name='rates'),
    path('rates/<str:from_currency>/<str:to_currency>/', views.RatePairView.as_view(), name='rate_pair'),
    path('convert/', views.ConvertView.as_view(), name='convert'),
    path('history/<str:from_currency>/<str:to_currency>/', views.RateHistoryView.as_view(), name='rate_history'),
    path('forex/stats/', views.ForexStatsView.as_view(), name='forex_stats'),
    path('forex/providers/', views.ForexProvidersView.as_view(), name='forex_providers'),
    path('forex/sync/', views.ForexSyncView.as_view(), name='forex_sync'),
]
