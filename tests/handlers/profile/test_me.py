from datetime import time
from unittest.mock import AsyncMock

import pytest

from src.bot.handlers.profile.me import handle_me
from src.i18n import i18n
from src.models import Role, User


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
        day_start=time(8, 0),
        day_end=time(20, 0),
    )

    with i18n.context():
        await handle_me(message, user)

    # Assert that message.answer was called with the correct user profile information
    expected = (
        "👤 Your Profile:\n"
        "Name: John Doe\n"
        "Username: @johndoe\n"
        "Role: patient\n"
        "Language: en\n"
        "Timezone: UTC\n"
        "Daylight Hours: 8:00 AM - 8:00 PM\n"
        "Privacy: Accepted"
    )

    message.answer.assert_called_once()
    sent_text = message.answer.call_args.args[0]
    assert sent_text == expected
