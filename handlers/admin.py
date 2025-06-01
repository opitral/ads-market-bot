import math
from contextlib import suppress

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from api.client import ApiClient
from api.enums import Endpoint
from api.exceptions import NoSuchEntityException
from api.views import UserView, SubjectView, CityView
from config_reader import config
from database.models import Role, User
from database.orm_queries import find_user_by_telegram_id, add_user, find_all_users, find_user_by_id, \
    set_user_allowed_groups_count, set_user_role
from keyboards.admin import main_kb, administration_kb, all_users_kb, PaginationCbData, UserInfoCbData, \
    user_settings_kb, UserAllowedChatsChangeCbData, UserRoleChangeCbData, all_subjects_kb, SubjectCbData, subject_kb, \
    SubjectNameChangeCbData, cancel_kb, CitiesCbData, all_cities_kb, SubjectDeleteCbData, CityCbData, city_kb, \
    CityNameChangeCbData, subjects_and_cities_kb, SubjectsCbData, CityDeleteCbData, create_city_kb, CitySubjectCdData, \
    back_kb

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
@router.message(F.text.lower().contains("вернуться в админку"))
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
                reply_markup=all_users_kb(users, page=page))

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
        await message.answer("Направления и города", reply_markup=subjects_and_cities_kb())
        await message.answer(f"Всего направлений: {len(subjects)}", reply_markup=all_subjects_kb(subjects))

    else:
        await message.answer("Направления не найдены", reply_markup=subjects_and_cities_kb())


@router.callback_query(SubjectCbData.filter())
async def subject_info_handler(callback: CallbackQuery, callback_data: SubjectCbData, session: AsyncSession):
    found_user = await find_user_by_telegram_id(session, str(callback.message.chat.id))
    client = ApiClient(found_user)
    try:
        response = client.get_by_id(Endpoint.SUBJECT, callback_data.subject_id)
        await callback.message.edit_text(
            text=f"Направление: {response.get('name')}",
            reply_markup=subject_kb(response.get('id'))
        )

    except NoSuchEntityException as ex:
        await callback.answer(ex.message)


class SetSubjectName(StatesGroup):
    setting_new_subject_name = State()


@router.callback_query(SubjectNameChangeCbData.filter())
async def change_subject_name_handler(callback: CallbackQuery, callback_data: SubjectNameChangeCbData,
                                      state: FSMContext):
    await callback.message.answer(f"Отправьте мне новое название направления", reply_markup=cancel_kb())
    await state.set_state(SetSubjectName.setting_new_subject_name)
    await state.update_data(subject_id=callback_data.subject_id)


@router.message(SetSubjectName.setting_new_subject_name, F.text.lower().contains("отменить"))
async def change_subject_name_cancel_handler(message: Message, state: FSMContext):
    await message.answer(text="Действие отменено", reply_markup=subjects_and_cities_kb())
    await state.clear()


@router.message(SetSubjectName.setting_new_subject_name, F.text)
async def set_subject_name_handler(message: Message, session: AsyncSession, state: FSMContext):
    await state.update_data(new_subject_name=message.text)
    data = await state.get_data()

    found_user = await find_user_by_telegram_id(session, str(message.chat.id))
    client = ApiClient(found_user)
    try:
        client.update(Endpoint.SUBJECT, SubjectView(
            _id=data["subject_id"],
            name=data["new_subject_name"]
        ).to_dict())

        await subjects_handler(message, session)
        await message.answer("Новое название направления установлено", reply_markup=subjects_and_cities_kb())
        await state.clear()

    except Exception as ex:
        await message.answer(str(ex))


@router.message(SetSubjectName.setting_new_subject_name)
async def set_subject_name_unknown_handler(message: Message):
    await message.answer("Отправьте мне текстовое сообщение")


@router.callback_query(CitiesCbData.filter())
async def subject_cities_handler(callback: CallbackQuery, callback_data: CitiesCbData, session: AsyncSession):
    found_user = await find_user_by_telegram_id(session, str(callback.message.chat.id))
    client = ApiClient(found_user)
    try:
        response = client.get_all(Endpoint.CITY, {
            "subjectId": callback_data.subject_id,
        })
        cities = response.get("responseList")
        if not cities:
            return await callback.answer("Города не найдены")

        await callback.message.edit_text(text=callback.message.text, reply_markup=all_cities_kb(cities))

    except Exception as ex:
        await callback.answer(str(ex))


@router.callback_query(CityCbData.filter())
async def subject_city_handler(callback: CallbackQuery, callback_data: CityCbData, session: AsyncSession):
    found_user = await find_user_by_telegram_id(session, str(callback.message.chat.id))
    client = ApiClient(found_user)
    try:
        response = client.get_by_id(Endpoint.CITY, callback_data.city_id)
        await callback.message.edit_text(
            text=callback.message.text + f"\nГород: {response.get('name')}",
            reply_markup=city_kb(response.get('id'), callback_data.subject_id)
        )

    except Exception as ex:
        await callback.answer(str(ex))


@router.callback_query(SubjectDeleteCbData.filter())
async def subject_delete_handler(callback: CallbackQuery, callback_data: SubjectDeleteCbData, session: AsyncSession):
    found_user = await find_user_by_telegram_id(session, str(callback.message.chat.id))
    client = ApiClient(found_user)
    try:
        client.delete(Endpoint.SUBJECT, callback_data.subject_id)
        await subjects_handler(callback.message, session)
        await callback.answer("Успешно")
        await callback.message.delete()

    except Exception as ex:
        await callback.answer(str(ex))


class SetCityName(StatesGroup):
    setting_new_city_name = State()


@router.callback_query(CityNameChangeCbData.filter())
async def change_city_name_handler(callback: CallbackQuery, callback_data: CityNameChangeCbData, state: FSMContext):
    await callback.message.answer(f"Отправьте мне новое название города", reply_markup=cancel_kb())
    await state.set_state(SetCityName.setting_new_city_name)
    await state.update_data(city_id=callback_data.city_id)


@router.message(SetCityName.setting_new_city_name, F.text.lower().contains("отменить"))
async def change_city_name_cancel_handler(message: Message, session: AsyncSession, state: FSMContext):
    await subjects_handler(message, session)
    await message.answer(text="Действие отменено")
    await state.clear()


@router.message(SetCityName.setting_new_city_name, F.text)
async def set_city_name_handler(message: Message, session: AsyncSession, state: FSMContext):
    await state.update_data(new_city_name=message.text)
    data = await state.get_data()

    found_user = await find_user_by_telegram_id(session, str(message.chat.id))
    client = ApiClient(found_user)
    try:
        client.update(Endpoint.CITY, CityView(
            _id=data["city_id"],
            name=data["new_city_name"]
        ).to_dict())

        await subjects_handler(message, session)
        await message.answer("Новое название города установлено")
        await state.clear()

    except Exception as ex:
        await message.answer(str(ex))


@router.message(SetCityName.setting_new_city_name)
async def set_city_name_unknown_handler(message: Message):
    await message.answer("Отправьте мне текстовое сообщение")


@router.callback_query(SubjectsCbData.filter())
async def all_subjects_cd_handler(callback: CallbackQuery, session: AsyncSession):
    found_user = await find_user_by_telegram_id(session, str(callback.message.chat.id))
    client = ApiClient(found_user)
    response = client.get_all(Endpoint.SUBJECT)
    subjects = response.get("responseList")
    if subjects:
        await callback.message.answer("Направления и города", reply_markup=subjects_and_cities_kb())
        await callback.message.answer(f"Всего направлений: {len(subjects)}", reply_markup=all_subjects_kb(subjects))

    else:
        await callback.message.answer("Направления не найдены")


@router.callback_query(CityDeleteCbData.filter())
async def city_delete_handler(callback: CallbackQuery, callback_data: CityDeleteCbData, session: AsyncSession):
    found_user = await find_user_by_telegram_id(session, str(callback.message.chat.id))
    client = ApiClient(found_user)
    try:
        client.delete(Endpoint.CITY, callback_data.city_id)
        await subjects_handler(callback.message, session)
        await callback.answer("Успешно")
        await callback.message.delete()

    except Exception as ex:
        await callback.answer(str(ex))


class NewSubject(StatesGroup):
    setting_subject_name = State()


@router.message(F.text.lower().contains("добавить направление"))
async def add_subject_handler(message: Message, state: FSMContext):
    await message.answer(f"Отправьте мне название направления", reply_markup=cancel_kb())
    await state.set_state(NewSubject.setting_subject_name)


@router.message(NewSubject.setting_subject_name, F.text.lower().contains("отменить"))
async def add_subject_cancel_handler(message: Message, session: AsyncSession, state: FSMContext):
    await subjects_handler(message, session)
    await message.answer(text="Действие отменено")
    await state.clear()


@router.message(NewSubject.setting_subject_name, F.text)
async def create_subject_handler(message: Message, session: AsyncSession, state: FSMContext):
    await state.update_data(new_subject_name=message.text)
    data = await state.get_data()

    found_user = await find_user_by_telegram_id(session, str(message.chat.id))
    client = ApiClient(found_user)
    try:
        client.create(Endpoint.SUBJECT, SubjectView(
            name=data["new_subject_name"]
        ).to_dict())

        await subjects_handler(message, session)
        await message.answer("Новое направление создано")
        await state.clear()

    except Exception as ex:
        await message.answer(str(ex))


@router.message(NewSubject.setting_subject_name)
async def add_subject_unknown_handler(message: Message):
    await message.answer("Отправьте мне текстовое сообщение")


class NewCity(StatesGroup):
    setting_city_subject_id = State()
    setting_city_name = State()


@router.message(F.text.lower().contains("добавить город"))
@router.message(NewCity.setting_city_name, F.text.lower().contains("назад"))
async def add_city_handler(message: Message, session: AsyncSession, state: FSMContext):
    found_user = await find_user_by_telegram_id(session, str(message.chat.id))
    client = ApiClient(found_user)
    try:
        response = client.get_all(Endpoint.SUBJECT)
        subjects = response.get("responseList")
        if not subjects:
            return message.answer("У вас нету добавленных направлений")

        await message.answer("Добавить город", reply_markup=cancel_kb())
        await message.answer("Выберите направление", reply_markup=create_city_kb(subjects))
        await state.set_state(NewCity.setting_city_subject_id)

    except Exception as ex:
        await message.answer(str(ex))


@router.callback_query(NewCity.setting_city_subject_id, CitySubjectCdData.filter())
async def set_new_city_subject_id_handler(callback: CallbackQuery, callback_data: CitySubjectCdData, state: FSMContext):
    await state.update_data(new_city_subject_id=callback_data.subject_id)
    await callback.message.answer("Отправьте мне название города", reply_markup=back_kb())
    await state.set_state(NewCity.setting_city_name)


@router.message(NewCity.setting_city_subject_id, F.text.lower().contains("отменить"))
async def add_city_subject_id_cancel_handler(message: Message, session: AsyncSession, state: FSMContext):
    await subjects_handler(message, session)
    await message.answer(text="Действие отменено")
    await state.clear()


@router.message(NewCity.setting_city_name, F.text)
async def create_city_handler(message: Message, session: AsyncSession, state: FSMContext):
    await state.update_data(new_city_name=message.text)
    data = await state.get_data()
    found_user = await find_user_by_telegram_id(session, str(message.chat.id))
    client = ApiClient(found_user)
    try:
        client.create(Endpoint.CITY, CityView(
            name=data["new_city_name"],
            subject_id=data["new_city_subject_id"]
        ).to_dict())

        await subjects_handler(message, session)
        await message.answer("Новый город создан")
        await state.clear()

    except Exception as ex:
        await message.answer(str(ex))
