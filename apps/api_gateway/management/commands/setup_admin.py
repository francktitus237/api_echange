"""
Create or promote a Django superuser from environment variables.

Configured via Dokploy env vars:
    DJANGO_SUPERUSER_USERNAME
    DJANGO_SUPERUSER_PASSWORD
    DJANGO_SUPERUSER_EMAIL   (optional)

If the user already exists (e.g. registered through the site), it is
promoted to staff/superuser and its password is reset to the env value.
Safe to run on every deploy.
"""
import os

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create or promote a superuser from DJANGO_SUPERUSER_* env vars"

    def handle(self, *args, **options):
        username = os.getenv("DJANGO_SUPERUSER_USERNAME", "").strip()
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD", "").strip()
        email = os.getenv("DJANGO_SUPERUSER_EMAIL", "").strip()

        if not username or not password:
            self.stdout.write(
                "DJANGO_SUPERUSER_USERNAME/PASSWORD not set — skipping admin setup."
            )
            return

        user, created = User.objects.get_or_create(
            username=username, defaults={"email": email}
        )
        if email and user.email != email:
            user.email = email
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password(password)
        user.save()

        action = "created" if created else "promoted/password reset"
        self.stdout.write(self.style.SUCCESS(f"Superuser {action}: {username}"))
