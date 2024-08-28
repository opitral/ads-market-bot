from aiogram import Router, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from api.client import ApiClient
from api.enums import Endpoint
from api.views import UserView, PriceView, GroupView
from config_reader import config
from database.orm_queries import is_vendor, find_user_by_telegram_id, add_user, add_group
from filters.chat_type import ChatTypeFilter
from handlers.client import default_client_handler
from keyboards.admin import main_kb as admin_main_kb
from keyboards.vendor import main_kb, subjects_kb, SubjectCbData, cities_kb, back_kb, CityCbData, \
    group_choose_kb

router = Router()
router.message.filter(ChatTypeFilter(is_group=False))


def main_kb_by_role(message: Message):
    if message.chat.id in config.ADMIN_TELEGRAM_IDS:
        return admin_main_kb()

    return main_kb()


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


class AddGroup(StatesGroup):
    subject = State()
    city = State()
    group = State()
    price = State()


@router.message(F.text.lower().contains("добавить группу"))
@router.message(AddGroup.city, F.text.lower().contains("назад"))
async def add_group_handler(message: Message, session: AsyncSession, state: FSMContext):
    if not await is_vendor(session, str(message.chat.id)):
        return await default_client_handler(message)

    found_user = await find_user_by_telegram_id(session, str(message.chat.id))
    client = ApiClient(found_user)
    try:
        response = client.get_all(Endpoint.SUBJECT)
        subjects = response.get("responseList")
        if not subjects:
            return await message.answer("Направления не добавлены")

        if not await state.get_state():
            await message.answer("Добавление группы", reply_markup=back_kb())

        await message.answer("Выберите направление", reply_markup=subjects_kb(subjects))
        await state.set_state(AddGroup.subject)

    except Exception as ex:
        await message.answer(str(ex))


@router.message(AddGroup.subject, F.text.lower().contains("назад"))
async def add_group_cancel_handler(message: Message, session: AsyncSession, state: FSMContext):
    if not await is_vendor(session, str(message.chat.id)):
        return await default_client_handler(message)

    await message.answer("Главное меню", reply_markup=main_kb_by_role(message))
    await state.clear()


@router.callback_query(AddGroup.subject, SubjectCbData.filter())
async def add_group_city_handler(callback: CallbackQuery, callback_data: SubjectCbData, session: AsyncSession,
                                 state: FSMContext):
    if not await is_vendor(session, str(callback.message.chat.id)):
        return await default_client_handler(callback.message)

    await state.update_data(subject_id=callback_data.subject_id)
    found_user = await find_user_by_telegram_id(session, str(callback.message.chat.id))
    client = ApiClient(found_user)
    try:
        response = client.get_all(Endpoint.CITY, {"subjectId": callback_data.subject_id})
        cities = response.get("responseList")
        if not cities:
            return await callback.answer("Города не добавлены")

        await callback.message.edit_text(
            text="Выберите город",
            reply_markup=cities_kb(cities)
        )
        await state.set_state(AddGroup.city)

    except Exception as ex:
        await callback.answer(str(ex))


@router.callback_query(AddGroup.city, CityCbData.filter())
async def add_group_group_handler(callback: CallbackQuery, callback_data: CityCbData, session: AsyncSession,
                                  state: FSMContext):
    if not await is_vendor(session, str(callback.message.chat.id)):
        return await default_client_handler(callback.message)

    await state.update_data(city_id=callback_data.city_id)
    await callback.answer()
    await callback.message.answer("Выберите группу", reply_markup=group_choose_kb())
    await state.set_state(AddGroup.group)


@router.message(AddGroup.group, F.text.lower().contains("назад"))
async def add_group_group_back_handler(message: Message, session: AsyncSession, state: FSMContext):
    if not await is_vendor(session, str(message.chat.id)):
        return await default_client_handler(message)

    found_user = await find_user_by_telegram_id(session, str(message.chat.id))
    client = ApiClient(found_user)
    try:
        data = await state.get_data()
        response = client.get_all(Endpoint.CITY, {"subjectId": data["subject_id"]})
        cities = response.get("responseList")
        if not cities:
            return await message.answer("Города не добавлены")

        await message.answer("Назад", reply_markup=back_kb())
        await message.answer(
            text="Выберите город",
            reply_markup=cities_kb(cities)
        )
        await state.set_state(AddGroup.city)

    except Exception as ex:
        await message.answer(str(ex))


@router.message(AddGroup.group, F.chat_shared)
async def add_group_price_handler(message: Message, session: AsyncSession, state: FSMContext):
    if not await is_vendor(session, str(message.chat.id)):
        return await default_client_handler(message)

    await state.update_data(group_telegram_id=str(message.chat_shared.chat_id))
    await state.update_data(group_name=message.chat_shared.title)
    await state.update_data(group_username=message.chat_shared.username)

    await message.answer("Отправьте мне прайс лист в формате:\n*кол-во дней - цена без закрепа/цена с закрепом*\n\n"
                         "Пример:\n`1 - 10/15\n7 - 50/75\n14 - 90/140\n30 - 170/270`", parse_mode=ParseMode.MARKDOWN,
                         reply_markup=back_kb())
    await state.set_state(AddGroup.price)


@router.message(AddGroup.price, F.text)
async def create_group_handler(message: Message, session: AsyncSession, state: FSMContext):
    if not await is_vendor(session, str(message.chat.id)):
        return await default_client_handler(message)

    price_list = []
    try:
        counts = [1, 7, 14, 30]
        index = 0
        data = message.text
        days = data.split("\n")
        if len(days) != 4:
            raise

        for day in days:
            day_details = day.split(" - ")
            count = int(day_details[0])
            if count != counts[index]:
                raise

            prices = day_details[1].split("/")
            price_without_pin = prices[0]
            price_with_pin = prices[1]
            price_list.append(PriceView(price_without_pin, price_with_pin))
            index += 1

    except Exception as ex:
        print(ex)
        return await message.answer("Ошибка парсинга, попробуйте еще раз")

    data = await state.get_data()
    found_user = await find_user_by_telegram_id(session, str(message.chat.id))
    client = ApiClient(found_user)
    try:
        await add_group(session, found_user.id, data.get("group_telegram_id"))
        client.create(Endpoint.GROUP, GroupView(
            city_id=data["city_id"],
            name=data.get("group_name"),
            link=data.get("group_link"),
            group_telegram_id=data.get("group_telegram_id"),
            user_telegram_id=message.chat.id,
            price_for_one_day=price_list[0],
            price_for_one_week=price_list[1],
            price_for_two_weeks=price_list[2],
            price_for_one_month=price_list[3]
        ).to_dict())
        await message.answer("Группа добавлена, теперь добавьте бота в эту группу и сделайте администратором", reply_markup=main_kb_by_role(message))
        await state.clear()

    except Exception as ex:
        await message.answer(str(ex))


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

    await message.answer("Неизвестная команда", reply_markup=main_kb_by_role(message))


@router.callback_query()
async def unknown_callback(callback: CallbackQuery):
    await callback.answer()
