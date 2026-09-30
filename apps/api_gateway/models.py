import hashlib
import secrets
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class APIClient(models.Model):
    TIER_CHOICES = [
        ('free', 'Free'),
        ('standard', 'Standard'),
        ('premium', 'Premium'),
        ('partner', 'Partner'),
    ]
    QUOTA_MAP = {
        'free': 100,
        'standard': 1000,
        'premium': 5000,
        'partner': 50000,
    }

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_clients')
    name = models.CharField(max_length=100)
    api_key_prefix = models.CharField(max_length=8)
    api_key_hash = models.CharField(max_length=64, unique=True)
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, default='free')
    quota_requests_per_hour = models.PositiveIntegerField(default=100)
    total_requests = models.PositiveBigIntegerField(default=0)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.tier}) - {self.api_key_prefix}..."

    @classmethod
    def generate_key(cls):
        raw_key = f"fxp_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        prefix = raw_key[:8]
        return raw_key, key_hash, prefix

    @classmethod
    def verify_key(cls, raw_key):
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        try:
            return cls.objects.get(api_key_hash=key_hash, is_active=True)
        except cls.DoesNotExist:
            return None


class AuditLog(models.Model):
    api_client = models.ForeignKey(APIClient, on_delete=models.SET_NULL, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    method = models.CharField(max_length=10)
    path = models.CharField(max_length=500)
    status_code = models.PositiveSmallIntegerField()
    ip_address = models.GenericIPAddressField(null=True)
    response_time_ms = models.PositiveIntegerField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.method} {self.path} - {self.status_code}"


class Subscription(models.Model):
    PLAN_CHOICES = [
        ('free', 'Free - 100 req/h'),
        ('standard', 'Standard - 1000 req/h - 9.99€/mois'),
        ('premium', 'Premium - 5000 req/h - 29.99€/mois'),
        ('partner', 'Partner - 50000 req/h - 99.99€/mois'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Payment'),
        ('active', 'Active'),
        ('trial', 'Trial'),
        ('past_due', 'Past Due'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='free')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)
    auto_renew = models.BooleanField(default=True)
    stripe_customer_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True, null=True)
    
    class Meta:
        verbose_name = "Subscription"
        verbose_name_plural = "Subscriptions"
    
    def __str__(self):
        return f"{self.user.username} - {self.plan} ({self.status})"
    
    def is_active(self):
        return self.status == 'active' and (self.end_date is None or self.end_date > timezone.now())
    
    def get_tier_from_plan(self):
        plan_to_tier = {
            'free': 'free',
            'standard': 'standard',
            'premium': 'premium',
            'partner': 'partner',
        }
        return plan_to_tier.get(self.plan, 'free')
    
    def update_api_client_tier(self):
        tier = self.get_tier_from_plan()
        api_client = self.user.api_clients.first()
        if api_client:
            api_client.tier = tier
            api_client.quota_requests_per_hour = APIClient.QUOTA_MAP.get(tier, 100)
            api_client.save()


class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
        ('manual', 'Manual (Admin)'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='EUR')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    language = models.CharField(max_length=5, default='fr', help_text="Langue du client pour les notifications")
    stripe_payment_intent_id = models.CharField(max_length=100, blank=True, null=True)
    paypal_order_id = models.CharField(max_length=100, blank=True, null=True)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, help_text="Notes pour paiement manuel")
    
    class Meta:
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.amount}€ ({self.status})"
    
    def mark_completed(self):
        self.status = 'completed'
        self.save()
        # Notifier le client (no-op si EMAIL_HOST non configuré)
        try:
            from apps.api_gateway.emails import send_payment_received
            send_payment_received(self)
        except Exception:
            pass
        # Activer l'abonnement
        self.subscription.status = 'active'
        self.subscription.start_date = timezone.now()
        # Calculer la date de fin (1 mois)
        from datetime import timedelta
        self.subscription.end_date = timezone.now() + timedelta(days=30)
        self.subscription.save()
        # Générer la clé API si elle n'existe pas
        if not self.user.api_clients.exists():
            raw_key, key_hash, prefix = APIClient.generate_key()
            tier = self.subscription.get_tier_from_plan()
            APIClient.objects.create(
                user=self.user,
                name=f'{self.subscription.plan.capitalize()} API Key',
                api_key_prefix=prefix,
                api_key_hash=key_hash,
                tier=tier,
                quota_requests_per_hour=APIClient.QUOTA_MAP.get(tier, 100),
            )
