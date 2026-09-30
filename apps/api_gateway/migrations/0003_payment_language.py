from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api_gateway', '0002_subscription_payment'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='language',
            field=models.CharField(default='fr', help_text='Langue du client pour les notifications', max_length=5),
        ),
    ]
