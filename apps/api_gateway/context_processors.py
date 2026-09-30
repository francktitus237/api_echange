"""Exposes language context (t dict, lang code, dir) to every template."""
from .i18n import get_lang, TRANSLATIONS, LANG_CHOICES, RTL_LANGS


def i18n(request):
    lang = get_lang(request)
    return {
        'lang': lang,
        'dir': 'rtl' if lang in RTL_LANGS else 'ltr',
        't': TRANSLATIONS[lang],
        'langs': LANG_CHOICES,
    }
