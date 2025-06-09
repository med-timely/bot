from typing import Optional

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import MaybeInaccessibleMessageUnion, Message


async def edit_or_answer(
    message: Optional[MaybeInaccessibleMessageUnion], answer: str, **kwargs
):
    if not message:
        return

    try:
        if isinstance(message, Message):
            return await message.edit_text(answer, **kwargs)

        return await message.answer(answer, **kwargs)
    except TelegramBadRequest:
        return await message.answer(answer, **kwargs)
