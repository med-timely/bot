from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from aiogram.types import User as TgUser
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import User
from src.services.user_service import UserService

from .database import DatabaseData


class UserData(DatabaseData, total=False):
    user_service: UserService
    user: User | None


class UserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, UserData], Awaitable[Any]],
        event: TelegramObject,
        data: UserData,
    ) -> Any:
        session: AsyncSession = data["session"]
        service: UserService = UserService(session)
        data["user_service"] = service

        tg_user: TgUser | None = data.get("event_from_user")
        if not tg_user:
            return await handler(event, data)

        # Get or create user
        user = await service.get_or_create_user(
            tg_user.id,
            tg_user.first_name,
            username=tg_user.username,
            last_name=tg_user.last_name,
            language_code=tg_user.language_code,
        )

        data["user"] = user
        return await handler(event, data)
