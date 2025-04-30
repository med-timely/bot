from cachetools import TTLCache
from sqlalchemy import select, insert, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import User


class UserService:
    """
    Service for managing user data with caching.

    This service handles user retrieval, creation, and updates with an in-memory
    TTL cache to improve performance.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.cache = TTLCache(maxsize=1000, ttl=300)  # 5-minute cache

    async def get(self, user_id: int) -> User | None:
        return await self.session.scalar(select(User).where(User.id == user_id))

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        return await self.session.scalar(
            select(User).where(User.telegram_id == telegram_id).limit(1)
        )

    async def get_or_create_user(
        self,
        telegram_id: int,
        first_name: str,
        *,
        username: str | None = None,
        last_name: str | None = None,
        language_code: str | None = None,
    ) -> User:
        # Check cache first
        if user := self.cache.get(telegram_id):
            return user

        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            stmt = (
                insert(User)
                .prefix_with("IGNORE", dialect="mariadb")
                .prefix_with("IGNORE", dialect="mysql")
                .values(
                    telegram_id=telegram_id,
                    first_name=first_name,
                    username=username,
                    last_name=last_name,
                    language_code=language_code,
                )
            )
            await self.session.execute(stmt)
            await self.session.commit()

            user = await self.get_by_telegram_id(telegram_id)

        # Update cache
        self.cache[telegram_id] = user

        return user

    async def select(self, ids: list[int]) -> list[User]:
        stmt = select(User).where(User.id.in_(ids))
        result = await self.session.execute(stmt)

        return list(result.scalars().all())

    async def accept_privacy(self, user_id: int):
        await self.session.execute(
            update(User).where(User.id == user_id).values(privacy_accepted=True)
        )
        await self.session.commit()

        # Update cache
        await self._update_cache(user_id)

    async def update(
        self,
        user_id: int,
        *,
        first_name: str | None = None,
        username: str | None = None,
        last_name: str | None = None,
        language_code: str | None = None,
        timezone: str | None = None,
        phone_number: str | None = None,
    ):
        values = {}
        if first_name is not None:
            values["first_name"] = first_name
        if username is not None:
            values["username"] = username
        if last_name is not None:
            values["last_name"] = last_name
        if language_code is not None:
            values["language_code"] = language_code
        if timezone is not None:
            values["timezone"] = timezone
        if phone_number is not None:
            values["phone_number"] = phone_number

        if values:
            await self.session.execute(
                update(User).where(User.id == user_id).values(**values)
            )
            await self.session.commit()

            # Update cache
            await self._update_cache(user_id)

    async def _update_cache(self, user_id: int):
        user = await self.get(user_id)
        if not user:
            return

        self.cache[user.telegram_id] = user
