"""
URL configuration for forex_platform project.
"""
from django.contrib import admin
from django.urls import path, include

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from apps.api_gateway import views as api_gateway_views

urlpatterns = [
    path('', api_gateway_views.home_view, name='home'),
    path('admin/', admin.site.urls),
    # User Interface
    path('register/', api_gateway_views.register_view, name='register'),
    path('login/', api_gateway_views.login_view, name='login'),
    path('logout/', api_gateway_views.logout_view, name='logout'),
    path('dashboard/', api_gateway_views.dashboard_view, name='dashboard'),
    path('payment/', api_gateway_views.payment_view, name='payment'),
    path('subscription/', api_gateway_views.subscription_view, name='subscription'),
    path('docs/', api_gateway_views.docs_view, name='docs'),
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    # API v1 endpoints
    path('api/v1/', include('apps.api_gateway.urls')),
]
