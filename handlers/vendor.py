from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from api.enums import Endpoint
from api.views import UserView
from database.orm_queries import is_vendor, find_user_by_telegram_id, add_user
from filters.chat_type import ChatTypeFilter
from api.client import ApiClient
from handlers.client import default_client_handler
from keyboards.vendor import main_kb

router = Router()
router.message.filter(ChatTypeFilter(is_group=False))


@router.message(Command("start"))
async def command_start_handler(message: Message, session: AsyncSession):
    if not await find_user_by_telegram_id(session, str(message.chat.id)):
        user = await add_user(session, str(message.chat.id), message.from_user.first_name, message.from_user.last_name,
                              message.from_user.username)
        api = ApiClient(user)
        api.create(Endpoint.USER, UserView(str(message.chat.id)).to_dict())

    if not await is_vendor(session, str(message.chat.id)):
        return await default_client_handler(message)

    await message.answer("👋 Здравствуйте", reply_markup=main_kb())


@router.message(F.text.lower().contains("добавить группу"))
async def add_group_handler(message: Message, session: AsyncSession):
    if not await is_vendor(session, str(message.chat.id)):
        return await default_client_handler(message)

    await message.answer("⚙️ В разработке")


@router.message(F.text.lower().contains("мои группы"))
async def my_groups_handler(message: Message, session: AsyncSession):
    if not await is_vendor(session, str(message.chat.id)):
        return await default_client_handler(message)

    await message.answer("⚙️ В разработке")


@router.message(F.text.lower().contains("создать объявление"))
async def create_post_handler(message: Message, session: AsyncSession):
    if not await is_vendor(session, str(message.chat.id)):
        return await default_client_handler(message)

    await message.answer("⚙️ В разработке")


@router.message(F.text.lower().contains("статистика"))
async def statistic_handler(message: Message, session: AsyncSession):
    if not await is_vendor(session, str(message.chat.id)):
        return await default_client_handler(message)

    await message.answer("⚙️ В разработке")


@router.message()
async def unknown_handler(message: Message, session: AsyncSession):
    if not await is_vendor(session, str(message.chat.id)):
        return await default_client_handler(message)

    await message.answer("Неизвестная команда", reply_markup=main_kb())


@router.callback_query()
async def unknown_callback(callback: CallbackQuery):
    await callback.answer()


@router.message()
async def unknown_handler(message: Message):
    await message.answer("Неизвестная команда")
