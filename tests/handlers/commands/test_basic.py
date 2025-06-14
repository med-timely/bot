from unittest.mock import AsyncMock

import pytest

from src.bot.handlers.commands.basic import handle_help
from src.i18n import i18n


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
