from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Seed forex providers and periodic sync tasks'

    def handle(self, *args, **options):
        from apps.forex.models import ForexProvider

        providers = [
            # ECB: free, no API key required — official daily rates (EUR base)
            {'code': 'ecb', 'name': 'European Central Bank', 'is_active': True, 'is_free': True, 'weight': 1.0, 'priority': 0},
            # Paid/free-tier providers — active but self-skip when no API key is set
            {'code': 'exchangerate_api', 'name': 'ExchangeRate-API', 'is_active': True, 'is_free': True, 'weight': 0.9, 'priority': 1},
            {'code': 'openexchangerates', 'name': 'Open Exchange Rates', 'is_active': True, 'is_free': True, 'weight': 0.9, 'priority': 2},
        ]
        for p in providers:
            obj, created = ForexProvider.objects.get_or_create(code=p['code'], defaults=p)
            self.stdout.write(('Created' if created else 'Exists') + f' provider: {p["code"]}')

        # Schedule periodic tasks (idempotent)
        try:
            from django_celery_beat.models import IntervalSchedule, PeriodicTask

            every_15m, _ = IntervalSchedule.objects.get_or_create(every=15, period=IntervalSchedule.MINUTES)
            hourly, _ = IntervalSchedule.objects.get_or_create(every=1, period=IntervalSchedule.HOURS)
            daily, _ = IntervalSchedule.objects.get_or_create(every=24, period=IntervalSchedule.HOURS)

            PeriodicTask.objects.get_or_create(
                name='sync_all_rates',
                defaults={'task': 'apps.forex.tasks.sync_all_rates', 'interval': every_15m},
            )
            PeriodicTask.objects.get_or_create(
                name='mark_stale_rates',
                defaults={'task': 'apps.forex.tasks.mark_stale_rates', 'interval': hourly},
            )
            PeriodicTask.objects.get_or_create(
                name='archive_daily_rates',
                defaults={'task': 'apps.forex.tasks.archive_daily_rates', 'interval': daily},
            )
            self.stdout.write(self.style.SUCCESS('Periodic tasks scheduled'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Could not schedule tasks: {e}'))
