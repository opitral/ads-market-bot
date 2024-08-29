from aiogram import Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_queries import get_group_by_telegram_id, add_message
from filters.chat_type import ChatTypeFilter

router = Router()
router.message.filter(ChatTypeFilter(is_group=True))


@router.message()
async def new_message_in_group(message: Message, session: AsyncSession):
    found_group = await get_group_by_telegram_id(session, str(message.chat.id))

    if found_group:
        await add_message(session, found_group.id)
