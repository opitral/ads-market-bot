from aiogram import Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Role
from database.orm_queries import get_group_by_telegram_id, add_message, find_user_by_id
from filters.chat_type import ChatTypeFilter

router = Router()
router.message.filter(ChatTypeFilter(is_group=True))


@router.message()
async def new_message_in_group(message: Message, session: AsyncSession):
    found_group = await get_group_by_telegram_id(session, str(message.chat.id))
    if found_group:
        group_owner = await find_user_by_id(session, found_group.user_id)
        if group_owner.role != Role.CLIENT:
            await add_message(session, found_group.id)
