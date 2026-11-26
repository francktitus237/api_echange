from django.db import migrations


CURRENCIES = [
    ('EUR', 'Euro', '€', '🇪🇺'),
    ('USD', 'US Dollar', '$', '🇺🇸'),
    ('JPY', 'Japanese Yen', '¥', '🇯🇵'),
    ('BGN', 'Bulgarian Lev', 'лв', '🇧🇬'),
    ('CZK', 'Czech Koruna', 'Kč', '🇨🇿'),
    ('DKK', 'Danish Krone', 'kr', '🇩🇰'),
    ('GBP', 'British Pound', '£', '🇬🇧'),
    ('HUF', 'Hungarian Forint', 'Ft', '🇭🇺'),
    ('PLN', 'Polish Zloty', 'zł', '🇵🇱'),
    ('RON', 'Romanian Leu', 'lei', '🇷🇴'),
    ('SEK', 'Swedish Krona', 'kr', '🇸🇪'),
    ('CHF', 'Swiss Franc', 'CHF', '🇨🇭'),
    ('ISK', 'Icelandic Króna', 'kr', '🇮🇸'),
    ('NOK', 'Norwegian Krone', 'kr', '🇳🇴'),
    ('TRY', 'Turkish Lira', '₺', '🇹🇷'),
    ('AUD', 'Australian Dollar', '$', '🇦🇺'),
    ('BRL', 'Brazilian Real', 'R$', '🇧🇷'),
    ('CAD', 'Canadian Dollar', '$', '🇨🇦'),
    ('CNY', 'Chinese Yuan', '¥', '🇨🇳'),
    ('HKD', 'Hong Kong Dollar', '$', '🇭🇰'),
    ('IDR', 'Indonesian Rupiah', 'Rp', '🇮🇩'),
    ('ILS', 'Israeli Shekel', '₪', '🇮🇱'),
    ('INR', 'Indian Rupee', '₹', '🇮🇳'),
    ('KRW', 'South Korean Won', '₩', '🇰🇷'),
    ('MXN', 'Mexican Peso', '$', '🇲🇽'),
    ('MYR', 'Malaysian Ringgit', 'RM', '🇲🇾'),
    ('NZD', 'New Zealand Dollar', '$', '🇳🇿'),
    ('PHP', 'Philippine Peso', '₱', '🇵🇭'),
    ('SGD', 'Singapore Dollar', '$', '🇸🇬'),
    ('THB', 'Thai Baht', '฿', '🇹🇭'),
    ('ZAR', 'South African Rand', 'R', '🇿🇦'),
    ('XAF', 'CFA Franc BEAC', 'FCFA', '🇨🇲'),
    ('XOF', 'CFA Franc BCEAO', 'FCFA', '🇸🇳'),
    ('KMF', 'Comorian Franc', 'CF', '🇰🇲'),
    ('MAD', 'Moroccan Dirham', 'DH', '🇲🇦'),
    ('NGN', 'Nigerian Naira', '₦', '🇳🇬'),
    ('GHS', 'Ghanaian Cedi', '₵', '🇬🇭'),
    ('KES', 'Kenyan Shilling', 'KSh', '🇰🇪'),
    ('DZD', 'Algerian Dinar', 'DA', '🇩🇿'),
    ('TND', 'Tunisian Dinar', 'DT', '🇹🇳'),
]


def seed_currencies(apps, schema_editor):
    Currency = apps.get_model('core', 'Currency')
    for code, name, symbol, flag in CURRENCIES:
        obj = Currency.objects.filter(pk=code).first()
        if obj:
            if not obj.flag:
                obj.flag = flag
                obj.save(update_fields=['flag'])
        else:
            Currency.objects.create(code=code, name=name, symbol=symbol, flag=flag)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_currencies, migrations.RunPython.noop),
    ]
