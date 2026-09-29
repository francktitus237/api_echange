from django.urls import path
from . import views

urlpatterns = [
    path('wallets/', views.WalletListCreateView.as_view(), name='wallets'),
    path('wallets/<str:currency_code>/transactions/', views.WalletTransactionsView.as_view(), name='wallet_transactions'),
    path('transfers/', views.TransferListView.as_view(), name='transfers'),
    path('transfers/create/', views.TransferCreateView.as_view(), name='transfer_create'),
    path('transfers/<str:reference>/', views.TransferDetailView.as_view(), name='transfer_detail'),
    path('wallets/credit/', views.WalletCreditView.as_view(), name='wallet_credit'),
]
