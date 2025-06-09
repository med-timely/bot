from unittest.mock import AsyncMock

from aiogram.utils.i18n import I18n
import pytest

from src.bot.handlers.commands.basic import handle_help, handle_me
from src.models import Role, User

i18n = I18n(path="locales")


@pytest.mark.asyncio
async def test_handle_help():
    message = AsyncMock()
    message.text = "/help"
    with i18n.context():
        await handle_help(message)
    # Assert that message.answer was called with the correct help text
    message.answer.assert_called_once_with(
        "🆘 Help:\n"
        "/me - Show your profile information\n"
        "/schedule - Create medication schedule\n"
        "/list - Show active medications\n"
        "/taken - Confirm dose taken\n"
        "/history - Show medication adherence history\n"
        "/stop - Stop medication schedule"
    )
