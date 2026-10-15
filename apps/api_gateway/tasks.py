import logging
from celery import shared_task
from django.utils.timezone import now
from datetime import timedelta

logger = logging.getLogger(__name__)

AUDIT_LOG_RETENTION_DAYS = 30


@shared_task
def cleanup_old_audit_logs():
    """Purge les logs d'audit de plus de 30 jours — évite que la table
    ne grossisse indéfiniment et ralentisse les requêtes."""
    from .models import AuditLog
    threshold = now() - timedelta(days=AUDIT_LOG_RETENTION_DAYS)
    deleted, _ = AuditLog.objects.filter(timestamp__lt=threshold).delete()
    logger.info(f"AuditLog cleanup: {deleted} entrées supprimées (> {AUDIT_LOG_RETENTION_DAYS}j).")
    return deleted
