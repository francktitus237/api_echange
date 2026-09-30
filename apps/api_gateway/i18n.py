"""
Lightweight i18n — dict-based translations, no gettext binaries needed.
Languages: fr (default), en, ar (RTL), es.
Resolution: ?lang= → cookie fxp_lang → Accept-Language → 'fr'.
"""


def get_lang(request) -> str:
    lang = request.GET.get('lang')
    if lang in TRANSLATIONS:
        return lang
    lang = request.COOKIES.get('fxp_lang')
    if lang in TRANSLATIONS:
        return lang
    for part in request.META.get('HTTP_ACCEPT_LANGUAGE', '').split(','):
        code = part.split(';')[0].strip()[:2]
        if code in TRANSLATIONS:
            return code
    return 'fr'


LANG_CHOICES = [
    ('fr', 'Français'),
    ('en', 'English'),
    ('ar', 'العربية'),
    ('es', 'Español'),
]

RTL_LANGS = ('ar',)


TRANSLATIONS = {
    # ===================== FRENCH (default) =====================
    'fr': {
        # Common
        'brand': 'ForexPlatform',
        'nav_dashboard': 'Dashboard',
        'nav_home': 'Accueil',
        'nav_docs': 'Documentation',
        'nav_logout': 'Déconnexion',
        'footer_tagline': "API de taux de change fiables pour vos applications",

        # Payment page
        'pay_title': 'Choisissez votre abonnement',
        'pay_subtitle': 'Sélectionnez un plan et une méthode de paiement pour activer votre compte',
        'step1': 'Étape 1 — Votre plan',
        'step2': 'Étape 2 — Méthode de paiement',
        'per_month': '/mois',
        'req_per_hour': 'requêtes/heure',
        'popular': 'Populaire',
        'current_plan': 'Plan actuel',
        'plan_free_desc': 'Pour tester et développer',
        'plan_standard_desc': 'Pour les petites entreprises',
        'plan_premium_desc': 'Pour les entreprises en croissance',
        'plan_partner_desc': 'Pour les grands partenaires',
        'method_card': 'Carte bancaire',
        'method_card_desc': 'Visa, Mastercard, Amex — sécurisé par Stripe',
        'method_paypal_desc': 'Payez avec votre compte PayPal',
        'method_manual': 'Virement / manuel',
        'method_manual_desc': 'Activation sous 24h après réception',
        'manual_info_title': 'Paiement manuel',
        'manual_info': 'Notre équipe vous contacte pour organiser le virement ou autre méthode. Votre compte est activé dès réception du paiement.',
        'summary': 'Récapitulatif',
        'summary_plan': 'Plan',
        'summary_quota': 'Quota',
        'summary_total': 'Total mensuel',
        'secure_note': 'Paiement chiffré SSL — vos données bancaires ne transitent jamais par nos serveurs',
        'renewal_note': 'Renouvellement mensuel — résiliable à tout moment',
        'cta_continue': 'Continuer vers le paiement',
        'cta_manual': 'Demander le paiement manuel',
        'cta_free': 'Activer le plan gratuit',
        'instant_activation': 'Activation instantanée',
        'back_dashboard': 'Dashboard',

        # Emails
        'email_welcome_subject': 'Bienvenue sur ForexPlatform API',
        'email_welcome_body': "Bonjour {name},\n\nVotre compte est créé. Connectez-vous à votre espace client pour choisir un plan et obtenir votre clé API :\n{site}/dashboard/\n\nDocumentation : {site}/docs/\n\n— L'équipe ForexPlatform",
        'email_paid_subject': 'Paiement reçu — abonnement activé',
        'email_paid_body': "Bonjour {name},\n\nVotre paiement de {amount} {currency} ({method}) est confirmé.\nVotre plan '{plan}' est actif jusqu'au {end}.\n\nVotre clé API est disponible dans votre dashboard :\n{site}/dashboard/\n\n— L'équipe ForexPlatform",
        'email_manual_subject': 'Demande de paiement reçue',
        'email_manual_body': "Bonjour {name},\n\nVotre demande de paiement manuel ({amount} {currency}, plan {plan}) est enregistrée — référence #{ref}.\nNotre équipe la valide sous 24h et votre abonnement sera activé automatiquement.\n\n— L'équipe ForexPlatform",
        'email_activation_subject': 'Votre plan {plan} est activé',
        'email_activation_body': "Bonjour {name},\n\nBonne nouvelle : votre abonnement '{plan}' est maintenant actif.\nVotre clé API est disponible dans votre dashboard :\n{site}/dashboard/\n\n— L'équipe ForexPlatform",
        'email_admin_manual_subject': '[Admin] Demande de paiement manuel — {name}',
        'email_admin_manual_body': "Une demande de paiement manuel attend votre validation.\n\nClient : {name} <{email}>\nPlan : {plan}\nMontant : {amount} {currency}\nRéférence : #{ref}\n\nValidez-la dans l'admin : {site}/admin/api_gateway/payment/",
    },

    # ===================== ENGLISH =====================
    'en': {
        'brand': 'ForexPlatform',
        'nav_dashboard': 'Dashboard',
        'nav_home': 'Home',
        'nav_docs': 'Documentation',
        'nav_logout': 'Log out',
        'footer_tagline': 'Reliable exchange rate API for your applications',

        'pay_title': 'Choose your plan',
        'pay_subtitle': 'Select a plan and a payment method to activate your account',
        'step1': 'Step 1 — Your plan',
        'step2': 'Step 2 — Payment method',
        'per_month': '/month',
        'req_per_hour': 'requests/hour',
        'popular': 'Popular',
        'current_plan': 'Current plan',
        'plan_free_desc': 'For testing and development',
        'plan_standard_desc': 'For small businesses',
        'plan_premium_desc': 'For growing companies',
        'plan_partner_desc': 'For large partners',
        'method_card': 'Bank card',
        'method_card_desc': 'Visa, Mastercard, Amex — secured by Stripe',
        'method_paypal_desc': 'Pay with your PayPal account',
        'method_manual': 'Bank transfer / manual',
        'method_manual_desc': 'Activated within 24h after receipt',
        'manual_info_title': 'Manual payment',
        'manual_info': 'Our team will contact you to arrange the transfer or another method. Your account is activated as soon as payment is received.',
        'summary': 'Order summary',
        'summary_plan': 'Plan',
        'summary_quota': 'Quota',
        'summary_total': 'Monthly total',
        'secure_note': 'SSL encrypted payment — your card details never touch our servers',
        'renewal_note': 'Monthly renewal — cancel anytime',
        'cta_continue': 'Continue to payment',
        'cta_manual': 'Request manual payment',
        'cta_free': 'Activate free plan',
        'instant_activation': 'Instant activation',
        'back_dashboard': 'Dashboard',

        'email_welcome_subject': 'Welcome to ForexPlatform API',
        'email_welcome_body': "Hi {name},\n\nYour account is ready. Sign in to your dashboard to pick a plan and get your API key:\n{site}/dashboard/\n\nDocumentation: {site}/docs/\n\n— The ForexPlatform team",
        'email_paid_subject': 'Payment received — subscription activated',
        'email_paid_body': "Hi {name},\n\nYour payment of {amount} {currency} ({method}) is confirmed.\nYour '{plan}' plan is active until {end}.\n\nYour API key is available in your dashboard:\n{site}/dashboard/\n\n— The ForexPlatform team",
        'email_manual_subject': 'Payment request received',
        'email_manual_body': "Hi {name},\n\nYour manual payment request ({amount} {currency}, {plan} plan) is registered — reference #{ref}.\nOur team validates it within 24h and your subscription will be activated automatically.\n\n— The ForexPlatform team",
        'email_activation_subject': 'Your {plan} plan is now active',
        'email_activation_body': "Hi {name},\n\nGood news: your '{plan}' subscription is now active.\nYour API key is available in your dashboard:\n{site}/dashboard/\n\n— The ForexPlatform team",
        'email_admin_manual_subject': '[Admin] Manual payment request — {name}',
        'email_admin_manual_body': "A manual payment request is waiting for validation.\n\nCustomer: {name} <{email}>\nPlan: {plan}\nAmount: {amount} {currency}\nReference: #{ref}\n\nApprove it in admin: {site}/admin/api_gateway/payment/",
    },

    # ===================== ARABIC (RTL) =====================
    'ar': {
        'brand': 'ForexPlatform',
        'nav_dashboard': 'لوحة التحكم',
        'nav_home': 'الرئيسية',
        'nav_docs': 'التوثيق',
        'nav_logout': 'تسجيل الخروج',
        'footer_tagline': 'واجهة برمجية موثوقة لأسعار الصرف لتطبيقاتك',

        'pay_title': 'اختر اشتراكك',
        'pay_subtitle': 'حدد الخطة وطريقة الدفع لتفعيل حسابك',
        'step1': 'الخطوة 1 — خطتك',
        'step2': 'الخطوة 2 — طريقة الدفع',
        'per_month': '/شهر',
        'req_per_hour': 'طلب/ساعة',
        'popular': 'الأكثر شيوعاً',
        'current_plan': 'الخطة الحالية',
        'plan_free_desc': 'للاختبار والتطوير',
        'plan_standard_desc': 'للشركات الصغيرة',
        'plan_premium_desc': 'للشركات النامية',
        'plan_partner_desc': 'للشركاء الكبار',
        'method_card': 'بطاقة بنكية',
        'method_card_desc': 'Visa وMastercard وAmex — آمن عبر Stripe',
        'method_paypal_desc': 'ادفع بحساب PayPal الخاص بك',
        'method_manual': 'تحويل بنكي / يدوي',
        'method_manual_desc': 'تفعيل خلال 24 ساعة بعد الاستلام',
        'manual_info_title': 'الدفع اليدوي',
        'manual_info': 'سيتواصل معك فريقنا لترتيب التحويل أو طريقة أخرى. يتم تفعيل حسابك فور استلام الدفعة.',
        'summary': 'ملخص الطلب',
        'summary_plan': 'الخطة',
        'summary_quota': 'الحصة',
        'summary_total': 'الإجمالي الشهري',
        'secure_note': 'دفع مشفر SSL — بياناتك البنكية لا تمر عبر خوادمنا أبداً',
        'renewal_note': 'تجديد شهري — إلغاء في أي وقت',
        'cta_continue': 'متابعة إلى الدفع',
        'cta_manual': 'طلب الدفع اليدوي',
        'cta_free': 'تفعيل الخطة المجانية',
        'instant_activation': 'تفعيل فوري',
        'back_dashboard': 'لوحة التحكم',

        'email_welcome_subject': 'مرحباً بك في ForexPlatform API',
        'email_welcome_body': "مرحباً {name},\n\nتم إنشاء حسابك. سجّل الدخول إلى لوحة التحكم لاختيار خطة والحصول على مفتاح API:\n{site}/dashboard/\n\nالتوثيق: {site}/docs/\n\n— فريق ForexPlatform",
        'email_paid_subject': 'تم استلام الدفع — تم تفعيل الاشتراك',
        'email_paid_body': "مرحباً {name},\n\nتم تأكيد دفعتك بمبلغ {amount} {currency} ({method}).\nخطتك '{plan}' نشطة حتى {end}.\n\nمفتاح API الخاص بك متاح في لوحة التحكم:\n{site}/dashboard/\n\n— فريق ForexPlatform",
        'email_manual_subject': 'تم استلام طلب الدفع',
        'email_manual_body': "مرحباً {name},\n\nتم تسجيل طلب الدفع اليدوي ({amount} {currency}, خطة {plan}) — المرجع #{ref}.\nيقوم فريقنا بالتحقق خلال 24 ساعة وسيتم تفعيل اشتراكك تلقائياً.\n\n— فريق ForexPlatform",
        'email_activation_subject': 'خطتك {plan} نشطة الآن',
        'email_activation_body': "مرحباً {name},\n\nخبر سار: اشتراكك '{plan}' نشط الآن.\nمفتاح API الخاص بك متاح في لوحة التحكم:\n{site}/dashboard/\n\n— فريق ForexPlatform",
        'email_admin_manual_subject': '[إدارة] طلب دفع يدوي — {name}',
        'email_admin_manual_body': "طلب دفع يدوي بانتظار الموافقة.\n\nالعميل: {name} <{email}>\nالخطة: {plan}\nالمبلغ: {amount} {currency}\nالمرجع: #{ref}\n\nوافق عليه في لوحة الإدارة: {site}/admin/api_gateway/payment/",
    },

    # ===================== SPANISH =====================
    'es': {
        'brand': 'ForexPlatform',
        'nav_dashboard': 'Panel',
        'nav_home': 'Inicio',
        'nav_docs': 'Documentación',
        'nav_logout': 'Cerrar sesión',
        'footer_tagline': 'API de tipos de cambio fiables para sus aplicaciones',

        'pay_title': 'Elija su plan',
        'pay_subtitle': 'Seleccione un plan y un método de pago para activar su cuenta',
        'step1': 'Paso 1 — Su plan',
        'step2': 'Paso 2 — Método de pago',
        'per_month': '/mes',
        'req_per_hour': 'solicitudes/hora',
        'popular': 'Popular',
        'current_plan': 'Plan actual',
        'plan_free_desc': 'Para probar y desarrollar',
        'plan_standard_desc': 'Para pequeñas empresas',
        'plan_premium_desc': 'Para empresas en crecimiento',
        'plan_partner_desc': 'Para grandes socios',
        'method_card': 'Tarjeta bancaria',
        'method_card_desc': 'Visa, Mastercard, Amex — seguro con Stripe',
        'method_paypal_desc': 'Pague con su cuenta PayPal',
        'method_manual': 'Transferencia / manual',
        'method_manual_desc': 'Activación en 24h tras la recepción',
        'manual_info_title': 'Pago manual',
        'manual_info': 'Nuestro equipo le contactará para organizar la transferencia u otro método. Su cuenta se activa al recibir el pago.',
        'summary': 'Resumen del pedido',
        'summary_plan': 'Plan',
        'summary_quota': 'Cuota',
        'summary_total': 'Total mensual',
        'secure_note': 'Pago cifrado SSL — sus datos bancarios nunca pasan por nuestros servidores',
        'renewal_note': 'Renovación mensual — cancele cuando quiera',
        'cta_continue': 'Continuar al pago',
        'cta_manual': 'Solicitar pago manual',
        'cta_free': 'Activar plan gratuito',
        'instant_activation': 'Activación instantánea',
        'back_dashboard': 'Panel',

        'email_welcome_subject': 'Bienvenido a ForexPlatform API',
        'email_welcome_body': "Hola {name},\n\nSu cuenta está lista. Inicie sesión en su panel para elegir un plan y obtener su clave API:\n{site}/dashboard/\n\nDocumentación: {site}/docs/\n\n— El equipo de ForexPlatform",
        'email_paid_subject': 'Pago recibido — suscripción activada',
        'email_paid_body': "Hola {name},\n\nSu pago de {amount} {currency} ({method}) está confirmado.\nSu plan '{plan}' está activo hasta {end}.\n\nSu clave API está disponible en su panel:\n{site}/dashboard/\n\n— El equipo de ForexPlatform",
        'email_manual_subject': 'Solicitud de pago recibida',
        'email_manual_body': "Hola {name},\n\nSu solicitud de pago manual ({amount} {currency}, plan {plan}) está registrada — referencia #{ref}.\nNuestro equipo la valida en 24h y su suscripción se activará automáticamente.\n\n— El equipo de ForexPlatform",
        'email_activation_subject': 'Su plan {plan} está activo',
        'email_activation_body': "Hola {name},\n\nBuenas noticias: su suscripción '{plan}' ya está activa.\nSu clave API está disponible en su panel:\n{site}/dashboard/\n\n— El equipo de ForexPlatform",
        'email_admin_manual_subject': '[Admin] Solicitud de pago manual — {name}',
        'email_admin_manual_body': "Una solicitud de pago manual espera validación.\n\nCliente: {name} <{email}>\nPlan: {plan}\nImporte: {amount} {currency}\nReferencia: #{ref}\n\nApruébela en el admin: {site}/admin/api_gateway/payment/",
    },
}
