import math
from contextlib import suppress

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from api.client import ApiClient
from api.enums import Endpoint
from api.exceptions import NoSuchEntityException
from api.views import UserView
from config_reader import config
from database.models import Role, User
from database.orm_queries import find_user_by_telegram_id, add_user, find_all_users, find_user_by_id, \
    set_user_allowed_groups_count, set_user_role
from keyboards.admin import main_kb, administration_kb, all_users_kb, PaginationCbData, UserInfoCbData, \
    user_settings_kb, UserAllowedChatsChangeCbData, UserRoleChangeCbData, all_subjects_kb, SubjectCbData, subject_kb

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
async def admin_panel_handler(message: Message):
    await message.answer("Административаная панель", reply_markup=administration_kb())


@router.message(F.text.lower().contains("в главное меню"))
async def main_menu_handler(message: Message):
    await message.answer("Главное меню", reply_markup=main_kb())


@router.message(F.text.lower().contains("пользователи"))
async def users_handler(message: Message, session: AsyncSession):
    users = await find_all_users(session)
    if users:
        await message.answer(f"Всего пользователей: {len(users)}", reply_markup=all_users_kb(users))

    else:
        await message.answer("Пользователей не найдено")


def get_user_info_text(user: User):
    first_name = user.first_name if user.first_name else ""
    last_name = user.last_name if user.last_name else ""
    full_name = f"{first_name} {last_name}"

    title = f"<a href='https://t.me/{user.username}'>{full_name}</a>" if user.username else full_name
    return (f"Пользователь: {title}\n"
            f"Telegram ID: <code>{user.telegram_id}</code>\n"
            f"Роль: {user.role.value}\n"
            f"Количество разрешенных чатов: {user.allowed_groups_count}\n")


@router.callback_query(UserInfoCbData.filter())
async def get_user_info_handler(callback: CallbackQuery, callback_data: UserInfoCbData, session: AsyncSession):
    found_user = await find_user_by_id(session, callback_data.user_id)
    if not found_user:
        return await callback.answer("Пользователь не найден")

    await callback.message.edit_text(
        text=get_user_info_text(found_user),
        reply_markup=user_settings_kb(found_user.id),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )
    await callback.answer()


@router.callback_query(PaginationCbData.filter())
async def make_pagination_handler(callback: CallbackQuery, callback_data: PaginationCbData, session: AsyncSession):
    page = callback_data.page
    limit = config.PAGE_LIMIT
    users = await find_all_users(session)

    if users:
        max_page = math.ceil(len(users) / limit) - 1
        if page > max_page or page < 0:
            await callback.answer("Такой страницы не существует")
            page = 0

        with suppress(TelegramBadRequest):
            await callback.message.edit_text(
                f"Всего пользователей: {len(users)}",
                reply_markup=await all_users_kb(users, page=page))

    else:
        await callback.message.edit_text("Пользователей не найдено")

    await callback.answer()


@router.callback_query(UserAllowedChatsChangeCbData.filter())
async def change_user_allowed_group_count_handler(callback: CallbackQuery, callback_data: UserAllowedChatsChangeCbData,
                                                  session: AsyncSession):
    found_user = await find_user_by_id(session, callback_data.user_id)

    if not found_user:
        return await callback.answer("Пользователь не найден")

    new_allowed_groups_count = found_user.allowed_groups_count + callback_data.value

    if new_allowed_groups_count < 0:
        return await callback.answer("Установлено минимальное значение")

    elif new_allowed_groups_count > 1000:
        return await callback.answer("Установлено максимальное значение")

    found_user = await set_user_allowed_groups_count(session, found_user, new_allowed_groups_count)

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=get_user_info_text(found_user),
            reply_markup=user_settings_kb(found_user.id),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
    await callback.answer()


@router.callback_query(UserRoleChangeCbData.filter())
async def change_user_role_handler(callback: CallbackQuery, callback_data: UserRoleChangeCbData, session: AsyncSession):
    found_user = await find_user_by_id(session, callback_data.user_id)

    if not found_user:
        return await callback.answer("Пользователь не найден")

    if found_user.role == Role.ADMIN:
        return await callback.answer("Нельзя изменить роль админа")

    elif found_user.role == Role.VENDOR:
        found_user = await set_user_role(session, found_user, Role.CLIENT)

    elif found_user.role == Role.CLIENT:
        found_user = await set_user_role(session, found_user, Role.VENDOR)

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=get_user_info_text(found_user),
            reply_markup=user_settings_kb(found_user.id),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
    await callback.answer()


@router.message(F.text.lower().contains("направления и города"))
async def subjects_handler(message: Message, session: AsyncSession):
    found_user = await find_user_by_telegram_id(session, str(message.chat.id))
    client = ApiClient(found_user)
    response = client.get_all(Endpoint.SUBJECT)
    subjects = response.get("responseList")
    if subjects:
        await message.answer(f"Всего направлений: {len(subjects)}", reply_markup=all_subjects_kb(subjects))

    else:
        await message.answer("Направления не найдены")


@router.callback_query(SubjectCbData.filter())
async def subject_info_handler(callback: CallbackQuery, callback_data: SubjectCbData, session: AsyncSession):
    found_user = await find_user_by_telegram_id(session, str(callback.message.chat.id))
    client = ApiClient(found_user)
    try:
        response = client.get_by_id(Endpoint.SUBJECT, callback_data.subject_id)
        await callback.message.edit_text(
            text=f"{response.get('id')}. {response.get('name')}",
            reply_markup=subject_kb(response.get('id'))
        )

    except NoSuchEntityException as ex:
        await callback.answer(ex.message)
