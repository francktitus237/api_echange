from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenBlacklistView
from . import views

urlpatterns = [
    # Auth
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/token/blacklist/', TokenBlacklistView.as_view(), name='token_blacklist'),
    # Health
    path('health/', views.HealthView.as_view(), name='health'),
    # Stripe webhook (signature-verified, no auth)
    path('webhooks/stripe/', views.StripeWebhookView.as_view(), name='stripe_webhook'),
    # Documentation HTML
    path('docs/', views.DocsHTMLView.as_view(), name='docs_html'),

    # API Keys
    path('api-keys/', views.APIKeyListView.as_view(), name='api_keys'),
    path('api-keys/create/', views.APIKeyCreateView.as_view(), name='api_key_create'),
    path('api-keys/<int:pk>/', views.APIKeyDeleteView.as_view(), name='api_key_delete'),
    # Forex
    path('', include('apps.forex.urls')),
    # Wallets & Transfers
    path('', include('apps.transfers.urls')),
]
