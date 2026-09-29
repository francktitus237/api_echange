"""
Automatic admin setup — runs on every deploy.

Priority:
  1. DJANGO_SUPERUSER_* env vars set  → create or promote that user,
     password reset to the env value.
  2. Otherwise → promote the FIRST registered user to superuser
     (the site owner who signed up first). No env vars needed.

Safe to run on every deploy — idempotent.
"""
import os

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create or promote a superuser automatically on deploy"

    def handle(self, *args, **options):
        username = os.getenv("DJANGO_SUPERUSER_USERNAME", "").strip()
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD", "").strip()
        email = os.getenv("DJANGO_SUPERUSER_EMAIL", "").strip()

        # Mode 1: explicit env vars → create or promote named user
        if username and password:
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
            return

        # Mode 2: no env vars → promote the first registered user (site owner)
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write("A superuser already exists — skipping.")
            return

        first_user = User.objects.order_by("date_joined", "pk").first()
        if not first_user:
            self.stdout.write("No users registered yet — skipping admin setup.")
            return

        first_user.is_staff = True
        first_user.is_superuser = True
        first_user.is_active = True
        first_user.save()
        self.stdout.write(
            self.style.SUCCESS(
                f"First user promoted to superuser: {first_user.username} "
                f"(password unchanged — the one set at registration)"
            )
        )
