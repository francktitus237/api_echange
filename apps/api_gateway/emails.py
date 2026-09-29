"""
Email notifications. Silently skipped when EMAIL_HOST is not configured —
never breaks the user request.
"""
import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def _send(to: str, subject: str, body: str) -> None:
    if not settings.EMAIL_HOST or not to:
        return
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [to],
                  fail_silently=True)
    except Exception as e:
        logger.warning(f'Email to {to} failed: {e}')


def send_welcome(user) -> None:
    _send(
        user.email,
        'Bienvenue sur ForexPlatform API',
        f"Bonjour {user.username},\n\n"
        "Votre compte est créé. Connectez-vous à votre espace client pour "
        "choisir un plan et obtenir votre clé API :\n"
        f"{settings.SITE_URL}/dashboard/\n\n"
        "Documentation : " + settings.SITE_URL + "/docs/\n\n"
        "— L'équipe ForexPlatform",
    )


def send_payment_received(payment) -> None:
    _send(
        payment.user.email,
        'Paiement reçu — abonnement activé',
        f"Bonjour {payment.user.username},\n\n"
        f"Votre paiement de {payment.amount} {payment.currency} "
        f"({payment.get_payment_method_display()}) est confirmé.\n"
        f"Votre plan '{payment.subscription.plan}' est actif jusqu'au "
        f"{payment.subscription.end_date:%d/%m/%Y}.\n\n"
        f"Votre clé API est disponible dans votre dashboard :\n"
        f"{settings.SITE_URL}/dashboard/\n\n"
        "— L'équipe ForexPlatform",
    )


def send_manual_payment_request(payment) -> None:
    _send(
        payment.user.email,
        'Demande de paiement reçue',
        f"Bonjour {payment.user.username},\n\n"
        f"Votre demande de paiement manuel ({payment.amount} "
        f"{payment.currency}, plan {payment.subscription.plan}) est "
        f"enregistrée — référence #{payment.id}.\n"
        "Notre équipe la valide sous 24h et votre abonnement sera activé "
        "automatiquement.\n\n"
        "— L'équipe ForexPlatform",
    )
