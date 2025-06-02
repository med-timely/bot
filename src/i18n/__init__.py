from contextlib import contextmanager

from aiogram.utils.i18n import I18n

i18n = I18n(path="locales", default_locale="en")


@contextmanager
def use_locale(locale: str):
    with i18n.context(), i18n.use_locale(locale):
        yield
