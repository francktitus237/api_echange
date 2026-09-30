"""
Email notifications — multilingual (fr/en/ar/es), matching the client's
language. Silently skipped when EMAIL_HOST is not configured —
never breaks the user request.
"""
import logging

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail

from .i18n import TRANSLATIONS

logger = logging.getLogger(__name__)


def _t(lang: str, key: str, **kw) -> str:
    text = TRANSLATIONS.get(lang, TRANSLATIONS['fr']).get(key, '')
    return text.format(**kw) if kw else text


def _send(to: str, subject: str, body: str) -> None:
    if not settings.EMAIL_HOST or not to:
        return
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [to],
                  fail_silently=True)
    except Exception as e:
        logger.warning(f'Email to {to} failed: {e}')


def send_welcome(user, lang: str = 'fr') -> None:
    _send(user.email, _t(lang, 'email_welcome_subject'),
          _t(lang, 'email_welcome_body', name=user.username, site=settings.SITE_URL))


def send_payment_received(payment) -> None:
    lang = getattr(payment, 'language', 'fr') or 'fr'
    _send(
        payment.user.email,
        _t(lang, 'email_paid_subject'),
        _t(lang, 'email_paid_body',
           name=payment.user.username, amount=payment.amount,
           currency=payment.currency,
           method=payment.get_payment_method_display(),
           plan=payment.subscription.plan,
           end=f"{payment.subscription.end_date:%d/%m/%Y}",
           site=settings.SITE_URL),
    )


def send_manual_payment_request(payment) -> None:
    """Client confirmation + alert to all superusers for validation."""
    lang = getattr(payment, 'language', 'fr') or 'fr'
    _send(
        payment.user.email,
        _t(lang, 'email_manual_subject'),
        _t(lang, 'email_manual_body',
           name=payment.user.username, amount=payment.amount,
           currency=payment.currency, plan=payment.subscription.plan,
           ref=payment.id),
    )
    # Notify admins — always in English (internal)
    for admin in User.objects.filter(is_superuser=True).exclude(email=''):
        _send(
            admin.email,
            _t('en', 'email_admin_manual_subject', name=payment.user.username),
            _t('en', 'email_admin_manual_body',
               name=payment.user.username, email=payment.user.email,
               plan=payment.subscription.plan, amount=payment.amount,
               currency=payment.currency, ref=payment.id,
               site=settings.SITE_URL),
        )


def send_subscription_activated(user, plan: str, lang: str = 'fr') -> None:
    _send(user.email, _t(lang, 'email_activation_subject', plan=plan),
          _t(lang, 'email_activation_body', name=user.username,
             plan=plan, site=settings.SITE_URL))
