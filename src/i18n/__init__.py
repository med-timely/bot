from contextlib import contextmanager

from aiogram.utils.i18n import I18n

i18n = I18n(path="locales", default_locale="en")


@contextmanager
def i18n_context(locale: str):
    """
    Context manager for thread-local i18n locale setting

    Args:
        locale: Language code (e.g., 'en', 'ru')
    """
    original = i18n.ctx_locale.get()
    i18n.ctx_locale.set(locale)
    try:
        yield
    finally:
        i18n.ctx_locale.set(original)
