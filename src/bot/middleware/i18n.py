from aiogram.utils.i18n import I18n
from aiogram.utils.i18n.middleware import SimpleI18nMiddleware


class I18nMiddleware(SimpleI18nMiddleware):
    def __init__(self, i18n: I18n):
        super().__init__(i18n)
