"""
URL configuration for forex_platform project.
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from apps.api_gateway import views as api_gateway_views

urlpatterns = [
    path('', RedirectView.as_view(url='/register/', permanent=False), name='home'),
    path('admin/', admin.site.urls),
    # User Interface
    path('register/', api_gateway_views.register_view, name='register'),
    path('payment/', api_gateway_views.payment_view, name='payment'),
    path('subscription/', api_gateway_views.subscription_view, name='subscription'),
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    # API v1 endpoints
    path('api/v1/', include('apps.api_gateway.urls')),
]
