import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.dispatcher.middlewares.data import MiddlewareData
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class DatabaseData(MiddlewareData, total=False):
    session: AsyncSession


class DatabaseMiddleware(BaseMiddleware):
    def __init__(self, sessionmaker):
        self.sessionmaker = sessionmaker  # SQLAlchemy async session factory

    async def __call__(
        self,
        handler: Callable[[TelegramObject, DatabaseData], Awaitable[Any]],
        event: TelegramObject,
        data: DatabaseData,
    ) -> Any:
        # Create a new session for each request
        logger.debug("Creating new database session for request")
        async with self.sessionmaker() as session:
            data["session"] = session  # Inject session into handler data

            try:
                result = await handler(event, data)  # Execute handler
                logger.debug("Committing database transaction")
                await session.commit()  # Commit transaction if no errors
            except Exception as e:
                logger.error("Rolling back database transaction due to error: %s", e)
                await session.rollback()  # Rollback on errors
                raise
            finally:
                logger.debug("Closing database session")
                await session.close()  # Always close the session

            return result
