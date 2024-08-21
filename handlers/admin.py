from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from api.client import ApiClient
from api.enums import Endpoint
from api.views import UserView
from database.models import Role
from database.orm_queries import find_user_by_telegram_id, add_user
from keyboards.admin import main_kb

from filters.chat_type import ChatTypeFilter, IsAdminFilter

router = Router()
router.message.filter(ChatTypeFilter(is_group=False), IsAdminFilter())


@router.message(Command("start"))
async def command_start_handler(message: Message, session: AsyncSession):
    if not await find_user_by_telegram_id(session, str(message.chat.id)):
        user = await add_user(session, str(message.chat.id), message.from_user.first_name, message.from_user.last_name,
                              message.from_user.username, role=Role.ADMIN, allowed_groups_count=100)
        api = ApiClient(user)
        api.create(Endpoint.USER, UserView(str(message.chat.id)).to_dict())

    await message.answer("👋 Здравствуйте, админ!", reply_markup=main_kb())


@router.message(F.text.lower().contains("админка"))
async def admin_panel_handler(message: Message, session: AsyncSession):
    await message.answer("⚙️ В разработке")
