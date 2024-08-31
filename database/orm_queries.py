from datetime import datetime, timedelta
from typing import List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import User, Role, Group, Message, Post


async def find_user_by_telegram_id(session: AsyncSession, telegram_id: str) -> User:
    query = select(User).options(selectinload(User.groups)).where(User.telegram_id == telegram_id)
    result = await session.execute(query)
    found_user = result.scalars().first()
    return found_user


async def find_user_by_id(session: AsyncSession, user_id: int) -> User:
    query = select(User).options(selectinload(User.groups)).where(User.id == user_id)
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


async def add_group(session: AsyncSession, user_id: int, telegram_id: str, city_id: int, subject_id: int) -> Group:
    group = Group(
        user_id=user_id,
        telegram_id=telegram_id,
        city_id=city_id,
        subject_id=subject_id
    )

    session.add(group)
    await session.commit()
    return group


async def get_user_groups(session: AsyncSession, user_id: int) -> List[Group]:
    query = select(Group).where(Group.user_id == user_id)
    result = await session.execute(query)
    found_groups = result.scalars().all()
    return list(found_groups)


async def get_group_by_telegram_id_and_user_telegram_id(session: AsyncSession, group_telegram_id: str,
                                                        user_telegram_id: str) -> Group:
    user = await find_user_by_telegram_id(session, user_telegram_id)
    query = select(Group).where(Group.telegram_id == group_telegram_id, Group.user_id == user.id)
    result = await session.execute(query)
    found_group = result.scalars().first()
    return found_group


async def get_group_by_id(session: AsyncSession, group_id: int) -> Group:
    query = select(Group).where(Group.id == group_id)
    result = await session.execute(query)
    found_group = result.scalars().first()
    return found_group


async def get_group_by_telegram_id(session: AsyncSession, group_telegram_id: str) -> Group:
    query = select(Group).where(Group.telegram_id == group_telegram_id)
    result = await session.execute(query)
    found_group = result.scalars().first()
    return found_group


async def delete_group(session: AsyncSession, group: Group):
    await session.delete(group)
    await session.commit()


async def add_message(session: AsyncSession, group_id: int):
    message = Message(
        group_id=group_id
    )
    session.add(message)
    await session.commit()


async def get_messages_count_last_7_days(session: AsyncSession, group_id: int) -> int:
    now = datetime.now()
    seven_days_ago = now - timedelta(days=7)

    query = select(func.count(Message.id)).where(
        Message.group_id == group_id,
        Message.created_at >= seven_days_ago
    )

    result = await session.execute(query)
    messages_count = result.scalar()
    return messages_count


async def add_post(session: AsyncSession, group_id: int, total_price: int):
    post = Post(
        group_id=group_id,
        total_price=total_price
    )
    session.add(post)
    await session.commit()
