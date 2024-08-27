from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, Role


async def find_user_by_telegram_id(session: AsyncSession, telegram_id: str) -> User:
    query = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(query)
    found_user = result.scalars().first()
    return found_user


async def find_user_by_id(session: AsyncSession, user_id: int) -> User:
    query = select(User).where(User.id == user_id)
    result = await session.execute(query)
    found_user = result.scalars().first()
    return found_user


async def is_vendor(session: AsyncSession, telegram_id: str) -> bool:
    found_user = await find_user_by_telegram_id(session, telegram_id)
    return found_user.role == Role.VENDOR or found_user.role == Role.ADMIN


async def add_user(session: AsyncSession, telegram_id: str, first_name: str, last_name: str, username: str,
                   role: Role = Role.CLIENT, allowed_groups_count: int = 3) -> User:
    user = User(telegram_id=telegram_id, first_name=first_name, last_name=last_name, username=username, role=role,
                allowed_groups_count=allowed_groups_count)
    session.add(user)
    await session.commit()
    return user


async def find_all_users(session: AsyncSession) -> List[User]:
    query = select(User).order_by(User.created_at)
    result = await session.execute(query)
    found_users = result.scalars().all()
    return list(found_users)


async def set_user_allowed_groups_count(session: AsyncSession, user: User, allowed_groups_count: int) -> User:
    user.allowed_groups_count = allowed_groups_count
    await session.commit()
    return user


async def set_user_role(session: AsyncSession, user: User, role: Role) -> User:
    user.role = role
    await session.commit()
    return user
