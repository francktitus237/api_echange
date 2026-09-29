"""
Payment providers — Stripe Checkout and PayPal Orders API.

Each function returns None when the provider is not configured (missing
credentials), so views can fall back to a clear "not configured" message.
"""
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def stripe_configured() -> bool:
    return bool(settings.STRIPE_SECRET_KEY)


def paypal_configured() -> bool:
    return bool(settings.PAYPAL_CLIENT_ID and settings.PAYPAL_CLIENT_SECRET)


def create_stripe_checkout(payment, plan_label: str) -> str | None:
    """Create a Stripe Checkout Session. Returns the hosted checkout URL."""
    if not stripe_configured():
        return None
    try:
        import stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY
        session = stripe.checkout.Session.create(
            mode='payment',
            line_items=[{
                'price_data': {
                    'currency': payment.currency.lower(),
                    'unit_amount': int(payment.amount * 100),
                    'product_data': {
                        'name': f'ForexPlatform — Plan {plan_label}',
                        'description': 'Abonnement mensuel API de taux de change',
                    },
                },
                'quantity': 1,
            }],
            metadata={'payment_id': payment.id, 'user_id': payment.user_id},
            success_url=f'{settings.SITE_URL}/payment/success/?session_id={{CHECKOUT_SESSION_ID}}',
            cancel_url=f'{settings.SITE_URL}/payment/cancel/',
        )
        payment.stripe_payment_intent_id = session.id
        payment.save(update_fields=['stripe_payment_intent_id'])
        return session.url
    except Exception as e:
        logger.error(f'Stripe checkout failed for payment {payment.id}: {e}')
        return None


def verify_stripe_session(session_id: str) -> bool:
    """Check on return from Stripe that the session was actually paid."""
    if not stripe_configured() or not session_id:
        return False
    try:
        import stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY
        session = stripe.checkout.Session.retrieve(session_id)
        return session.payment_status == 'paid'
    except Exception as e:
        logger.error(f'Stripe session verify failed: {e}')
        return False


def handle_stripe_webhook(payload: bytes, sig_header: str) -> dict | None:
    """Verify signature and return the event, or None if invalid/unhandled."""
    if not stripe_configured() or not settings.STRIPE_WEBHOOK_SECRET:
        return None
    try:
        import stripe
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        logger.warning(f'Stripe webhook signature rejected: {e}')
        return None
    if event['type'] == 'checkout.session.completed':
        return event['data']['object']
    return None


# ---------- PayPal (Orders v2 REST — no deprecated SDK needed) ----------

def _paypal_base() -> str:
    return ('https://api-m.sandbox.paypal.com' if settings.PAYPAL_SANDBOX
            else 'https://api-m.paypal.com')


def _paypal_token() -> str | None:
    try:
        r = requests.post(
            f'{_paypal_base()}/v1/oauth2/token',
            auth=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_CLIENT_SECRET),
            data={'grant_type': 'client_credentials'},
            timeout=10,
        )
        r.raise_for_status()
        return r.json()['access_token']
    except Exception as e:
        logger.error(f'PayPal token failed: {e}')
        return None


def create_paypal_order(payment, plan_label: str) -> str | None:
    """Create a PayPal order. Returns the buyer approval URL."""
    if not paypal_configured():
        return None
    token = _paypal_token()
    if not token:
        return None
    try:
        r = requests.post(
            f'{_paypal_base()}/v2/checkout/orders',
            headers={'Authorization': f'Bearer {token}',
                     'Content-Type': 'application/json'},
            json={
                'intent': 'CAPTURE',
                'purchase_units': [{
                    'reference_id': str(payment.id),
                    'description': f'ForexPlatform — Plan {plan_label}',
                    'amount': {
                        'currency_code': payment.currency,
                        'value': str(payment.amount),
                    },
                }],
                'application_context': {
                    'return_url': f'{settings.SITE_URL}/payment/paypal/return/',
                    'cancel_url': f'{settings.SITE_URL}/payment/cancel/',
                },
            },
            timeout=10,
        )
        r.raise_for_status()
        order = r.json()
        payment.paypal_order_id = order['id']
        payment.save(update_fields=['paypal_order_id'])
        for link in order['links']:
            if link['rel'] == 'approve':
                return link['href']
    except Exception as e:
        logger.error(f'PayPal order create failed for payment {payment.id}: {e}')
    return None


def capture_paypal_order(order_id: str) -> bool:
    """Capture an approved PayPal order. True when payment captured."""
    if not paypal_configured() or not order_id:
        return False
    token = _paypal_token()
    if not token:
        return False
    try:
        r = requests.post(
            f'{_paypal_base()}/v2/checkout/orders/{order_id}/capture',
            headers={'Authorization': f'Bearer {token}',
                     'Content-Type': 'application/json'},
            timeout=10,
        )
        r.raise_for_status()
        return r.json().get('status') == 'COMPLETED'
    except Exception as e:
        logger.error(f'PayPal capture failed for order {order_id}: {e}')
        return False
