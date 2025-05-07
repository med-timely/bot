import asyncio
import logging
import random
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.dispatcher.middlewares.data import MiddlewareData
from aiogram.types import TelegramObject
from asyncmy.errors import MySQLError
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class DatabaseData(MiddlewareData, total=False):
    session: AsyncSession


class DatabaseMiddleware(BaseMiddleware):
    def __init__(self, sessionmaker):
        self.sessionmaker = sessionmaker  # SQLAlchemy async session factory
        self.max_retries = 3
        self.retry_delay = 0.5

    def _should_retry(self, exception, attempt):
        """Determine if the operation should be retried based on the exception and attempt number."""
        is_connection_error = getattr(exception.orig, "errno", None) in (2006, 2013)
        return is_connection_error and attempt < self.max_retries - 1

    async def __call__(
        self,
        handler: Callable[[TelegramObject, DatabaseData], Awaitable[Any]],
        event: TelegramObject,
        data: DatabaseData,
    ) -> Any:
        for attempt in range(self.max_retries):
            try:
                # Create a new session for each request
                logger.debug("Creating new database session for request")
                async with self.sessionmaker() as session:
                    data["session"] = session  # Inject session into handler data

                    try:
                        result = await handler(event, data)  # Execute handler
                        logger.debug("Committing database transaction")
                        await session.commit()  # Commit transaction if no errors
                    except Exception as e:
                        logger.error(
                            "Rolling back database transaction due to error: %s", e
                        )
                        await session.rollback()  # Rollback on errors
                        raise
                    finally:
                        logger.debug("Closing database session")

                    return result
            except (OperationalError, MySQLError, DBAPIError) as e:
                if self._should_retry(e, attempt):
                    delay = min(self.retry_delay * 2**attempt, 8)  # cap at 8 s
                    await asyncio.sleep(delay + random.random())
                    continue
                raise
