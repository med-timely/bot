from unittest.mock import AsyncMock

import pytest

from src.bot.handlers.commands.basic import handle_help, handle_me
from src.models import Role, User


@pytest.mark.asyncio
async def test_handle_help():
    message = AsyncMock()
    message.text = "/help"
    await handle_help(message)
    # Assert that message.answer was called with the correct help text
    message.answer.assert_called_once_with(
        "🆘 Help:\n"
        "/me - Show your profile information\n"
        "/schedule - Create medication schedule\n"
        "/list - Show active medications\n"
        "/taken - Confirm dose taken"
    )


@pytest.mark.asyncio
async def test_handle_me():
    message = AsyncMock()
    message.text = "/me"
    user = User(
        first_name="John",
        last_name="Doe",
        username="johndoe",
        role=Role.PATIENT,
        language_code="en",
        timezone="UTC",
        privacy_accepted=True,
    )
    await handle_me(message, user)
    # Assert that message.answer was called with the correct user profile information
    message.answer.assert_called_once_with(
        "👤 Your Profile:\n"
        "Name: John Doe\n"
        "Username: @johndoe\n"
        "Role: patient\n"
        "Language: en\n"
        "Timezone: UTC\n"
        "Privacy: Accepted"
    )
