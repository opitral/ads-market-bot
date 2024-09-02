import json
from datetime import datetime, timedelta
from urllib.parse import urlparse

from aiogram import Router, F
from aiogram.enums import ParseMode, ContentType
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from api.client import ApiClient
from api.enums import Endpoint, PublicationType
from api.views import UserView, PriceView, GroupView, PostView, PublicationView, ButtonView
from config_reader import config
from database.orm_queries import is_vendor, find_user_by_telegram_id, add_user, add_group, get_user_groups, \
    get_group_by_telegram_id_and_user_telegram_id, delete_group, get_messages_count_last_7_days, add_post, \
    get_total_price_last_days, get_total_price_all_time
from filters.chat_type import ChatTypeFilter
from handlers.client import default_client_handler
from keyboards.admin import main_kb as admin_main_kb
from keyboards.vendor import main_kb, subjects_kb, SubjectCbData, cities_kb, back_kb, CityCbData, \
    group_choose_kb, all_groups_kb, GroupCbData, group_kb, GroupWorkTimesCbData, GroupPostsIntervalCbData, \
    GroupPriceListCbData, GroupDeleteCbData, submit_delete_kb, GroupDeleteSubmitCbData, GroupDeleteCancelCbData, \
    calendar_kb, skip_kb, publication_kb, submit_post_kb, statistic_samples_kb

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


class MyGroups(StatesGroup):
    subject = State()
    city = State()
    group = State()


class GroupWorkTimes(StatesGroup):
    work_times = State()


class GroupPostsInterval(StatesGroup):
    interval = State()


class GroupPriceList(StatesGroup):
    price_list = State()


class CreatePost(StatesGroup):
    subject = State()
    city = State()
    group = State()
    calendar = State()
    post = State()
    button = State()
    submit = State()


class Statistic(StatesGroup):
    sample = State()
    subject = State()
    city = State()
    group = State()


@router.message(F.text.lower().contains("добавить группу"))
@router.message(AddGroup.city, F.text.lower().contains("назад"))
async def add_group_handler(message: Message, session: AsyncSession, state: FSMContext):
    if not await is_vendor(session, str(message.chat.id)):
        return await default_client_handler(message)

    found_user = await find_user_by_telegram_id(session, str(message.chat.id))

    if len(found_user.groups) >= found_user.allowed_groups_count:
        return await message.answer("Лимит на добавление групп исчерпан, "
                                    "свяжитесь с @parlament_er для увеличения лимита")

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
@router.message(MyGroups.subject, F.text.lower().contains("назад"))
@router.message(GroupWorkTimes.work_times, F.text.lower().contains("назад"))
@router.message(GroupPostsInterval.interval, F.text.lower().contains("назад"))
@router.message(GroupPriceList.price_list, F.text.lower().contains("назад"))
@router.message(CreatePost.subject, F.text.lower().contains("назад"))
@router.message(CreatePost.submit, F.text.lower().contains("отменить"))
@router.message(Statistic.sample, F.text.lower().contains("назад"))
async def cancel_handler(message: Message, session: AsyncSession, state: FSMContext):
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

    if await get_group_by_telegram_id_and_user_telegram_id(session,
                                                           str(message.chat_shared.chat_id), str(message.chat.id)):
        return await message.answer("Вы уже добавили эту группу")

    await state.update_data(group_telegram_id=str(message.chat_shared.chat_id))
    await state.update_data(group_name=message.chat_shared.title)
    await state.update_data(group_username=message.chat_shared.username)

    await message.answer("Отправьте мне прайс лист в формате:\n*кол-во дней - цена без закрепа/цена с закрепом*\n\n"
                         "Пример:\n<code>1 - 10/15\n7 - 50/75\n14 - 90/140\n30 - 170/270</code>",
                         parse_mode=ParseMode.HTML,
                         reply_markup=back_kb())
    await state.set_state(AddGroup.price)


@router.message(AddGroup.price, F.text.lower().contains("назад"))
async def add_group_price_back_handler(message: Message, session: AsyncSession, state: FSMContext):
    if not await is_vendor(session, str(message.chat.id)):
        return await default_client_handler(message)

    await message.answer("Выберите группу", reply_markup=group_choose_kb())
    await state.set_state(AddGroup.group)


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
            price_without_pin = int(prices[0])
            price_with_pin = int(prices[1])
            price_list.append(PriceView(price_without_pin, price_with_pin))
            index += 1

    except Exception:
        return await message.answer("Ошибка парсинга, попробуйте еще раз")

    data = await state.get_data()
    found_user = await find_user_by_telegram_id(session, str(message.chat.id))
    client = ApiClient(found_user)
    try:
        await add_group(session, found_user.id, data.get("group_telegram_id"),
                        city_id=data["city_id"], subject_id=data["subject_id"])
        client.create(Endpoint.GROUP, GroupView(
            city_id=data["city_id"],
            name=data.get("group_name"),
            link=data.get("group_link"),
            group_telegram_id=data.get("group_telegram_id"),
            user_telegram_id=str(message.chat.id),
            price_for_one_day=price_list[0],
            price_for_one_week=price_list[1],
            price_for_two_weeks=price_list[2],
            price_for_one_month=price_list[3]
        ).to_dict())
        await message.answer("Группа добавлена, теперь добавьте бота в эту группу и сделайте администратором",
                             reply_markup=main_kb_by_role(message))
        await state.clear()

    except Exception as ex:
        await message.answer(str(ex))


@router.message(F.text.lower().contains("мои группы"))
@router.message(MyGroups.city, F.text.lower().contains("назад"))
async def my_groups_handler(message: Message, session: AsyncSession, state: FSMContext):
    if not await is_vendor(session, str(message.chat.id)):
        return await default_client_handler(message)

    found_user = await find_user_by_telegram_id(session, str(message.chat.id))
    client = ApiClient(found_user)
    groups = await get_user_groups(session, found_user.id)
    if not groups:
        return await message.answer("У вас нету добавленных групп")

    subjects_dict = {}
    cities = {}
    for group in groups:
        try:
            subject = client.get_by_id(Endpoint.SUBJECT, group.subject_id)
            if subject.get("id") not in subjects_dict:
                subjects_dict[subject.get("id")] = subject.get("name")

            if subject.get("id") in cities:
                cities[subject.get("id")].append(group.city_id)

            else:
                cities[subject.get("id")] = [group.city_id]

        except Exception as ex:
            await message.answer(str(ex))

    subjects = []
    for key, value in subjects_dict.items():
        subjects.append(
            {
                "id": key,
                "name": value
            }
        )
    if not await state.get_state():
        await message.answer("Мои группы", reply_markup=back_kb())

    await state.update_data(cities=cities)
    await message.answer("Выберите направление", reply_markup=subjects_kb(subjects))
    await state.set_state(MyGroups.subject)


@router.callback_query(MyGroups.subject, SubjectCbData.filter())
async def my_groups_cities_handler(callback: CallbackQuery, callback_data: SubjectCbData,
                                   session: AsyncSession, state: FSMContext):
    if not await is_vendor(session, str(callback.message.chat.id)):
        return await default_client_handler(callback.message)

    await state.update_data(subject_id=callback_data.subject_id)
    found_user = await find_user_by_telegram_id(session, str(callback.message.chat.id))
    client = ApiClient(found_user)
    data = await state.get_data()
    try:
        response = client.get_all(Endpoint.CITY, {"ids": data["cities"][callback_data.subject_id]})
        cities = response.get("responseList")
        if not cities:
            return await callback.answer("Города не добавлены")

        await callback.message.edit_text(
            text="Выберите город",
            reply_markup=cities_kb(cities)
        )
        await state.set_state(MyGroups.city)

    except Exception as ex:
        await callback.answer(str(ex))


@router.callback_query(MyGroups.city, CityCbData.filter())
async def my_groups_groups_handler(callback: CallbackQuery, callback_data: CityCbData, session: AsyncSession,
                                   state: FSMContext):
    if not await is_vendor(session, str(callback.message.chat.id)):
        return await default_client_handler(callback.message)

    await state.update_data(city_id=callback_data.city_id)
    found_user = await find_user_by_telegram_id(session, str(callback.message.chat.id))
    client = ApiClient(found_user)
    try:
        response = client.get_all(Endpoint.GROUP, {
            "cityId": callback_data.city_id,
            "userTelegramId": callback.message.chat.id
        })
        groups = response.get("responseList")
        await callback.message.edit_text(
            text="Выберите группу",
            reply_markup=all_groups_kb(groups)
        )
        await state.set_state(MyGroups.group)

    except Exception as ex:
        await callback.answer(str(ex))


@router.message(MyGroups.group, F.text.lower().contains("назад"))
async def my_groups_groups_back_handler(message: Message, session: AsyncSession, state: FSMContext):
    if not await is_vendor(session, str(message.chat.id)):
        return await default_client_handler(message)

    data = await state.get_data()
    found_user = await find_user_by_telegram_id(session, str(message.chat.id))
    client = ApiClient(found_user)
    try:
        response = client.get_all(Endpoint.CITY, {"ids": data["cities"][data["subject_id"]]})
        cities = response.get("responseList")
        if not cities:
            return await message.answer("Города не добавлены")

        await message.answer(
            text="Выберите город",
            reply_markup=cities_kb(cities)
        )
        await state.set_state(MyGroups.city)

    except Exception as ex:
        await message.answer(str(ex))


async def get_group_info(message: Message, session: AsyncSession, group_id: int) -> str:
    found_user = await find_user_by_telegram_id(session, str(message.chat.id))
    client = ApiClient(found_user)
    group = client.get_by_id(Endpoint.GROUP, group_id)

    city = client.get_by_id(Endpoint.CITY, group.get("cityId"))
    subject = client.get_by_id(Endpoint.SUBJECT, city.get("subjectId"))

    members_count = await message.bot.get_chat_member_count(chat_id=group.get('groupTelegramId'))

    title = f"<a href='https://t.me/{group.get('link')}'>{group.get('name')}</a>" if group.get('link') else group.get(
        'name')
    telegram_id = group.get('groupTelegramId')
    working_hours_start = group.get('workingHoursStart')
    working_hours_end = group.get('workingHoursEnd') if group.get('workingHoursEnd') != "00:00" else "24:00"
    post_interval_in_minutes = group.get('postIntervalInMinutes')
    price_for_one_day = (f"{group.get('priceForOneDay').get('withoutPin')}/"
                         f"{group.get('priceForOneDay').get('withPin')}")
    price_for_one_week = (f"{group.get('priceForOneWeek').get('withoutPin')}/"
                          f"{group.get('priceForOneWeek').get('withPin')}")
    price_for_two_weeks = (f"{group.get('priceForTwoWeeks').get('withoutPin')}/"
                           f"{group.get('priceForTwoWeeks').get('withPin')}")
    price_for_one_month = (f"{group.get('priceForOneMonth').get('withoutPin')}/"
                           f"{group.get('priceForOneMonth').get('withPin')}")
    average_post_views = group.get('averagePostViews')

    group_local = await get_group_by_telegram_id_and_user_telegram_id(session, telegram_id, str(message.chat.id))
    messages_count_last_7_days = await get_messages_count_last_7_days(session, group_local.id)

    return (f"Название: {title}\n"
            f"Telegram ID: <code>{telegram_id}</code>\n"
            f"Направление: {subject.get('name')}\n"
            f"Город: {city.get('name')}\n\n"
            f"Начало работы: {working_hours_start}\n"
            f"Конец работы: {working_hours_end}\n"
            f"Интервал публикаций: {post_interval_in_minutes} минут\n\n"
            f"Цена за один день: {price_for_one_day}\n"
            f"Цена за одну неделю: {price_for_one_week}\n"
            f"Цена за две недели: {price_for_two_weeks}\n"
            f"Цена за один месяц: {price_for_one_month}\n\n"
            f"Кол-во участников: {members_count}\n"
            f"Среднее кол-во просмотров одной рекламы: {average_post_views}\n"
            f"Кол-во сообщений за последние 7 дней: {messages_count_last_7_days}")


@router.callback_query(MyGroups.group, GroupCbData.filter())
async def my_groups_group_handler(callback: CallbackQuery, callback_data: GroupCbData, session: AsyncSession,
                                  state: FSMContext):
    if not await is_vendor(session, str(callback.message.chat.id)):
        return await default_client_handler(callback.message)

    try:
        await callback.message.edit_text(
            text=await get_group_info(callback.message, session, callback_data.group_id),
            parse_mode=ParseMode.HTML,
            reply_markup=group_kb(callback_data.group_id)
        )
        await state.clear()
        await callback.message.answer(f"Главное меню", reply_markup=main_kb_by_role(callback.message))

    except TelegramAPIError:
        return await callback.answer("Бот не является участником группы")

    except Exception as ex:
        return await callback.answer(str(ex))


@router.callback_query(GroupWorkTimesCbData.filter())
async def change_group_work_times_handler(callback: CallbackQuery, callback_data: GroupCbData, session: AsyncSession,
                                          state: FSMContext):
    if not await is_vendor(session, str(callback.message.chat.id)):
        return await default_client_handler(callback.message)

    await callback.message.answer("Отправьте мне рабочие часы группы в формате:\n"
                                  "<b>время начала работы-время конца работы</b>\n"
                                  "*Минуты будут автоматически установлены в ноли\n\n"
                                  "Пример:\n"
                                  "<code>12:00-20:00</code>", parse_mode=ParseMode.HTML, reply_markup=back_kb())

    await callback.answer()
    await state.update_data(group_id=callback_data.group_id)
    await state.set_state(GroupWorkTimes.work_times)


@router.message(GroupWorkTimes.work_times, F.text)
async def set_group_work_times_handler(message: Message, session: AsyncSession, state: FSMContext):
    if not await is_vendor(session, str(message.chat.id)):
        return await default_client_handler(message)

    try:
        data = message.text
        start_time, end_time = data.split("-")
        if end_time.split(":")[0] == "24":
            end_time = "00:00"
        start_time = datetime.strptime(start_time, "%H:%M").replace(minute=0)
        end_time = datetime.strptime(end_time, "%H:%M").replace(minute=0)
        if start_time > end_time and end_time.time() != datetime.strptime("00:00", "%H:%M").time():
            raise

    except Exception:
        return await message.answer("Ошибка во время парсинга, попробуйте еще раз")

    found_user = await find_user_by_telegram_id(session, str(message.chat.id))
    client = ApiClient(found_user)
    data = await state.get_data()
    try:
        client.update(Endpoint.GROUP, {
            "id": data["group_id"],
            "workingHoursStart": start_time.time().strftime("%H:%M"),
            "workingHoursEnd": end_time.time().strftime("%H:%M"),
        })
        await message.answer(
            text=await get_group_info(message, session, data["group_id"]),
            parse_mode=ParseMode.HTML,
            reply_markup=group_kb(data["group_id"])
        )
        await message.answer("Рабочие часы обновлены", reply_markup=main_kb_by_role(message))
        await state.clear()

    except Exception as ex:
        await message.answer(str(ex))


@router.callback_query(GroupPostsIntervalCbData.filter())
async def change_group_posts_interval_handler(callback: CallbackQuery, callback_data: GroupCbData,
                                              session: AsyncSession, state: FSMContext):
    if not await is_vendor(session, str(callback.message.chat.id)):
        return await default_client_handler(callback.message)

    await callback.message.answer("Отправьте мне интервал между публикациями в минутах\n"
                                  "*Значение должно быть кратным 30\n\n"
                                  "Пример:\n"
                                  "<code>120</code>", parse_mode=ParseMode.HTML, reply_markup=back_kb())

    await callback.answer()
    await state.update_data(group_id=callback_data.group_id)
    await state.set_state(GroupPostsInterval.interval)


@router.message(GroupPostsInterval.interval, F.text)
async def set_group_posts_interval_handler(message: Message, session: AsyncSession, state: FSMContext):
    if not await is_vendor(session, str(message.chat.id)):
        return await default_client_handler(message)

    found_user = await find_user_by_telegram_id(session, str(message.chat.id))
    client = ApiClient(found_user)
    data = await state.get_data()

    try:
        interval = int(message.text)
        if interval % 30 != 0:
            raise

    except Exception:
        return await message.answer("Ошибка во время парсинга, попробуйте еще раз")

    try:
        client.update(Endpoint.GROUP, {
            "id": data["group_id"],
            "postIntervalInMinutes": interval
        })

        await message.answer(
            text=await get_group_info(message, session, data["group_id"]),
            reply_markup=group_kb(data["group_id"]),
            parse_mode=ParseMode.HTML
        )
        await message.answer("Интервал установлен", reply_markup=main_kb_by_role(message))
        await state.clear()

    except Exception as ex:
        await message.answer(str(ex))


@router.callback_query(GroupPriceListCbData.filter())
async def change_group_price_list_handler(callback: CallbackQuery, callback_data: GroupCbData, session: AsyncSession,
                                          state: FSMContext):
    if not await is_vendor(session, str(callback.message.chat.id)):
        return await default_client_handler(callback.message)

    await callback.message.answer("Отправьте мне прайс лист в формате:\n"
                                  "*кол-во дней - цена без закрепа/цена с закрепом*\n\n"
                                  "Пример:\n<code>1 - 10/15\n7 - 50/75\n14 - 90/140\n30 - 170/270</code>",
                                  parse_mode=ParseMode.HTML,
                                  reply_markup=back_kb())

    await callback.answer()
    await state.update_data(group_id=callback_data.group_id)
    await state.set_state(GroupPriceList.price_list)


@router.message(GroupPriceList.price_list, F.text)
async def set_group_price_list_handler(message: Message, session: AsyncSession, state: FSMContext):
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
            price_without_pin = int(prices[0])
            price_with_pin = int(prices[1])
            price_list.append(PriceView(price_without_pin, price_with_pin))
            index += 1

    except Exception:
        return await message.answer("Ошибка парсинга, попробуйте еще раз")

    data = await state.get_data()
    found_user = await find_user_by_telegram_id(session, str(message.chat.id))
    client = ApiClient(found_user)
    try:
        client.update(Endpoint.GROUP, {
            "id": data["group_id"],
            "priceForOneDay": price_list[0].to_dict(),
            "priceForOneWeek": price_list[1].to_dict(),
            "priceForTwoWeeks": price_list[2].to_dict(),
            "priceForOneMonth": price_list[3].to_dict(),
        })
        await message.answer(
            text=await get_group_info(message, session, data["group_id"]),
            reply_markup=group_kb(data["group_id"]),
            parse_mode=ParseMode.HTML
        )
        await message.answer("Прайс лист установлен", reply_markup=main_kb_by_role(message))
        await state.clear()

    except Exception as ex:
        await message.answer(str(ex))


@router.callback_query(GroupDeleteCbData.filter())
async def group_delete_handler(callback: CallbackQuery, callback_data: GroupDeleteCbData, session: AsyncSession):
    if not await is_vendor(session, str(callback.message.chat.id)):
        return await default_client_handler(callback.message)

    found_user = await find_user_by_telegram_id(session, str(callback.message.chat.id))
    client = ApiClient(found_user)
    try:
        group = client.get_by_id(Endpoint.GROUP, callback_data.group_id)

    except Exception as ex:
        return await callback.message.answer(str(ex))

    await callback.message.edit_text(
        text=f"Вы уверены, что хотите удалить группу <b>{group.get('name')}</b>?",
        parse_mode=ParseMode.HTML,
        reply_markup=submit_delete_kb(group.get('id'))
    )


@router.callback_query(GroupDeleteSubmitCbData.filter())
async def group_delete_submit_handler(callback: CallbackQuery, callback_data: GroupDeleteSubmitCbData,
                                      session: AsyncSession):
    if not await is_vendor(session, str(callback.message.chat.id)):
        return await default_client_handler(callback.message)

    found_user = await find_user_by_telegram_id(session, str(callback.message.chat.id))
    client = ApiClient(found_user)
    try:
        group = client.get_by_id(Endpoint.GROUP, callback_data.group_id)
        group_local = await get_group_by_telegram_id_and_user_telegram_id(session, group.get("groupTelegramId"),
                                                                          str(callback.message.chat.id))
        await delete_group(session, group_local)
        client.delete(Endpoint.GROUP, callback_data.group_id)
        await callback.message.edit_text(f"Группа <b>{group.get('name')}</b> удалена", parse_mode=ParseMode.HTML)

    except Exception as ex:
        return await callback.message.answer(str(ex))


@router.callback_query(GroupDeleteCancelCbData.filter())
async def group_delete_cancel(callback: CallbackQuery, callback_data: GroupDeleteCancelCbData, session: AsyncSession):
    if not await is_vendor(session, str(callback.message.chat.id)):
        return await default_client_handler(callback.message)

    await callback.message.edit_text(
        text=await get_group_info(callback.message, session, callback_data.group_id),
        parse_mode=ParseMode.HTML,
        reply_markup=group_kb(callback_data.group_id))


@router.message(F.text.lower().contains("создать объявление"))
@router.message(CreatePost.city, F.text.lower().contains("назад"))
async def create_post_handler(message: Message, session: AsyncSession, state: FSMContext):
    if not await is_vendor(session, str(message.chat.id)):
        return await default_client_handler(message)

    found_user = await find_user_by_telegram_id(session, str(message.chat.id))
    client = ApiClient(found_user)
    groups = await get_user_groups(session, found_user.id)
    if not groups:
        return await message.answer("У вас нету добавленных групп")

    subjects_dict = {}
    cities = {}
    for group in groups:
        try:
            subject = client.get_by_id(Endpoint.SUBJECT, group.subject_id)
            if subject.get("id") not in subjects_dict:
                subjects_dict[subject.get("id")] = subject.get("name")

            if subject.get("id") in cities:
                cities[subject.get("id")].append(group.city_id)

            else:
                cities[subject.get("id")] = [group.city_id]

        except Exception as ex:
            await message.answer(str(ex))

    subjects = []
    for key, value in subjects_dict.items():
        subjects.append(
            {
                "id": key,
                "name": value
            }
        )
    if not await state.get_state():
        await message.answer("Создать объявление", reply_markup=back_kb())

    await state.update_data(cities=cities)
    await message.answer("Выберите направление", reply_markup=subjects_kb(subjects))
    await state.set_state(CreatePost.subject)


@router.callback_query(CreatePost.subject, SubjectCbData.filter())
async def create_post_city_handler(callback: CallbackQuery, callback_data: SubjectCbData, session: AsyncSession,
                                   state: FSMContext):
    if not await is_vendor(session, str(callback.message.chat.id)):
        return await default_client_handler(callback.message)

    await state.update_data(subject_id=callback_data.subject_id)
    found_user = await find_user_by_telegram_id(session, str(callback.message.chat.id))
    client = ApiClient(found_user)
    data = await state.get_data()
    try:
        response = client.get_all(Endpoint.CITY, {"ids": data["cities"][callback_data.subject_id]})
        cities = response.get("responseList")
        if not cities:
            return await callback.answer("Города не добавлены")

        await callback.message.edit_text(
            text="Выберите город",
            reply_markup=cities_kb(cities)
        )
        await state.set_state(CreatePost.city)

    except Exception as ex:
        await callback.answer(str(ex))


@router.callback_query(CreatePost.city, CityCbData.filter())
async def create_post_groups_handler(callback: CallbackQuery, callback_data: CityCbData, session: AsyncSession,
                                     state: FSMContext):
    if not await is_vendor(session, str(callback.message.chat.id)):
        return await default_client_handler(callback.message)

    await state.update_data(city_id=callback_data.city_id)
    found_user = await find_user_by_telegram_id(session, str(callback.message.chat.id))
    client = ApiClient(found_user)
    try:
        response = client.get_all(Endpoint.GROUP, {
            "cityId": callback_data.city_id,
            "userTelegramId": callback.message.chat.id
        })
        groups = response.get("responseList")
        await callback.message.edit_text(
            text="Выберите группу",
            reply_markup=all_groups_kb(groups)
        )
        await state.set_state(CreatePost.group)

    except Exception as ex:
        await callback.answer(str(ex))


@router.message(CreatePost.group, F.text.lower().contains("назад"))
async def create_post_groups_back_handler(message: Message, session: AsyncSession, state: FSMContext):
    if not await is_vendor(session, str(message.chat.id)):
        return await default_client_handler(message)

    data = await state.get_data()
    found_user = await find_user_by_telegram_id(session, str(message.chat.id))
    client = ApiClient(found_user)
    try:
        response = client.get_all(Endpoint.CITY, {"ids": data["cities"][data["subject_id"]]})
        cities = response.get("responseList")
        if not cities:
            return await message.answer("Города не добавлены")

        await message.answer(
            text="Выберите город",
            reply_markup=cities_kb(cities)
        )
        await state.set_state(CreatePost.city)

    except Exception as ex:
        await message.answer(str(ex))


@router.callback_query(CreatePost.group, GroupCbData.filter())
async def create_post_calendar_handler(callback: CallbackQuery, callback_data: GroupCbData, session: AsyncSession,
                                       state: FSMContext):
    if not await is_vendor(session, str(callback.message.chat.id)):
        return await default_client_handler(callback.message)

    await state.update_data(group_id=callback_data.group_id)
    await callback.message.answer("Откройте календарь и выберите нужные даты/время",
                                  reply_markup=calendar_kb(callback_data.group_id))
    await state.set_state(CreatePost.calendar)


@router.message(CreatePost.calendar, F.text.lower().contains("назад"))
async def create_post_calendar_back_handler(message: Message, session: AsyncSession, state: FSMContext):
    if not await is_vendor(session, str(message.chat.id)):
        return await default_client_handler(message)

    found_user = await find_user_by_telegram_id(session, str(message.chat.id))
    client = ApiClient(found_user)
    data = await state.get_data()
    try:
        response = client.get_all(Endpoint.GROUP, {
            "cityId": data["city_id"],
            "userTelegramId": message.chat.id
        })
        groups = response.get("responseList")
        await message.answer("Назад", reply_markup=back_kb())
        await message.answer(
            text="Выберите группу",
            reply_markup=all_groups_kb(groups)
        )
        await state.set_state(CreatePost.group)

    except Exception as ex:
        await message.answer(str(ex))


@router.message(CreatePost.calendar, F.content_type == ContentType.WEB_APP_DATA)
async def create_post_post_handler(message: Message, session: AsyncSession, state: FSMContext):
    if not await is_vendor(session, str(message.chat.id)):
        return await default_client_handler(message)

    await state.update_data(calendar=message.web_app_data.data)
    await message.answer("Отправьте мне публикацию, она может состоять из фото, видео, гиф или просто текста",
                         reply_markup=back_kb())

    await state.set_state(CreatePost.post)


@router.message(CreatePost.post, F.text.lower().contains("назад"))
async def create_post_post_back_handler(message: Message, session: AsyncSession, state: FSMContext):
    if not await is_vendor(session, str(message.chat.id)):
        return await default_client_handler(message)

    data = await state.get_data()
    await message.answer("Откройте календарь и выберите нужные даты/время",
                         reply_markup=calendar_kb(data["group_id"]))
    await state.set_state(CreatePost.calendar)


@router.message(CreatePost.post,
                F.content_type.in_([ContentType.TEXT, ContentType.PHOTO, ContentType.VIDEO, ContentType.ANIMATION]))
async def create_post_button_handler(message: Message, session: AsyncSession, state: FSMContext):
    if not await is_vendor(session, str(message.chat.id)):
        return await default_client_handler(message)

    if message.content_type == ContentType.PHOTO:
        await state.update_data(publication_type=PublicationType.PHOTO,
                                file_id=message.photo[-1].file_id, text=message.html_text)

    elif message.content_type == ContentType.VIDEO:
        await state.update_data(publication_type=PublicationType.VIDEO,
                                file_id=message.video.file_id, text=message.html_text)

    elif message.content_type == ContentType.ANIMATION:
        await state.update_data(publication_type=PublicationType.ANIMATION,
                                file_id=message.animation.file_id, text=message.html_text)

    elif message.content_type == ContentType.TEXT:
        await state.update_data(publication_type=PublicationType.TEXT,
                                file_id=None, text=message.html_text)

    await message.answer("Отправьте мне кнопку в формате:\n<b>текст кнопки | [ссылка]</b>\n\n"
                         "Пример:\n<code>Перейти | https://www.google.com/</code>",
                         reply_markup=skip_kb(), parse_mode=ParseMode.HTML)
    await state.set_state(CreatePost.button)


@router.message(CreatePost.button, F.text.lower().contains("назад"))
async def create_post_button_back_handler(message: Message, session: AsyncSession, state: FSMContext):
    if not await is_vendor(session, str(message.chat.id)):
        return await default_client_handler(message)

    await message.answer("Отправьте мне публикацию, она может состоять из фото, видео, гиф или просто текста",
                         reply_markup=back_kb())
    await state.set_state(CreatePost.post)


def get_publication_info(data):
    publication_type = data["publication_type"]
    file_id = data["file_id"]
    text = data["text"]
    button_text, button_url = data.get("button_text"), data.get("button_url")

    return {
        "publication_type": publication_type,
        "text": text,
        "file_id": file_id,
        "button": {
            "text": button_text,
            "url": button_url
        }
    }


def get_post_info(data):
    calendar = json.loads(data["calendar"])
    posts = []
    for post in calendar.get("posts"):
        date = datetime.strptime(post.get('date'), "%Y-%m-%d").date()
        time = datetime.strptime(post.get('time'), "%H:%M:%S").time()
        posts.append({
            "date": date,
            "time": time,
            "with_pin": post.get('withPin')
        })

    return {
        "group_id": data.get("group_id"),
        "total_price": calendar.get("totalPrice"),
        "posts": posts
    }


@router.message(CreatePost.button, F.text.lower().contains("пропустить"))
async def create_post_skip_handler(message: Message, session: AsyncSession, state: FSMContext):
    if not await is_vendor(session, str(message.chat.id)):
        return await default_client_handler(message)

    data = await state.get_data()
    publication_info = get_publication_info(data)
    if publication_info["publication_type"] == PublicationType.TEXT:
        await message.bot.send_message(message.chat.id,
                                       publication_info["text"],
                                       reply_markup=publication_kb(publication_info["button"]),
                                       parse_mode=ParseMode.HTML)

    elif publication_info["publication_type"] == PublicationType.PHOTO:
        await message.bot.send_photo(message.chat.id,
                                     photo=publication_info["file_id"],
                                     caption=publication_info["text"],
                                     reply_markup=publication_kb(publication_info["button"]),
                                     parse_mode=ParseMode.HTML)

    elif publication_info["publication_type"] == PublicationType.VIDEO:
        await message.bot.send_video(message.chat.id,
                                     video=publication_info["file_id"],
                                     caption=publication_info["text"],
                                     reply_markup=publication_kb(publication_info["button"]),
                                     parse_mode=ParseMode.HTML)

    elif publication_info["publication_type"] == PublicationType.ANIMATION:
        await message.bot.send_animation(message.chat.id,
                                         animation=publication_info["file_id"],
                                         caption=publication_info["text"],
                                         reply_markup=publication_kb(publication_info["button"]),
                                         parse_mode=ParseMode.HTML)

    post_info = get_post_info(data)
    found_user = await find_user_by_telegram_id(session, str(message.chat.id))
    client = ApiClient(found_user)
    try:
        group = client.get_by_id(Endpoint.GROUP, post_info.get("group_id"))

    except Exception as ex:
        return await message.answer(str(ex))

    posts = []
    for post in post_info.get("posts"):
        posts.append(f"{post['date'].strftime('%m-%d')} {post['time'].strftime('%H:%M')}"
                     f"({'с закрепом' if post['with_pin'] else 'без закрепа'})")

    await message.answer(text=f"Группа: {group.get('name')}\n"
                              f"Cтоимость: {post_info.get('total_price')}\n"
                              f"Будет опубликован: {', '.join(posts)}",
                         reply_markup=submit_post_kb())

    await state.set_state(CreatePost.submit)


def is_valid_url(url):
    parsed_url = urlparse(url)
    return all([parsed_url.scheme, parsed_url.netloc])


@router.message(CreatePost.button, F.text)
async def create_post_button_valid_handler(message: Message, session: AsyncSession, state: FSMContext):
    if not await is_vendor(session, str(message.chat.id)):
        return await default_client_handler(message)

    try:
        button = message.text
        text, url = button.split(" | ")
        if not is_valid_url(url):
            return await message.answer("Некорректная ссылка, попробуйте еще раз")

    except Exception:
        return await message.answer("Ошибка во время парсинга, попробуйте еще раз")

    await state.update_data(button_text=text, button_url=url)
    await create_post_skip_handler(message, session, state)


@router.message(CreatePost.submit, F.text.lower().contains("назад"))
async def create_post_submit_back_handler(message: Message, session: AsyncSession, state: FSMContext):
    if not await is_vendor(session, str(message.chat.id)):
        return await default_client_handler(message)

    await message.answer("Отправьте мне кнопку в формате:\n<b>текст кнопки | [ссылка]</b>\n\n"
                         "Пример:\n<code>Перейти | [https://www.google.com/]</code>",
                         reply_markup=skip_kb(), parse_mode=ParseMode.HTML)
    await state.set_state(CreatePost.button)


@router.message(CreatePost.submit, F.text.lower().contains("подтвердить"))
async def create_post_submit_ok_handler(message: Message, session: AsyncSession, state: FSMContext):
    if not await is_vendor(session, str(message.chat.id)):
        return await default_client_handler(message)

    data = await state.get_data()
    found_user = await find_user_by_telegram_id(session, str(message.chat.id))
    client = ApiClient(found_user)
    publication_info = get_publication_info(data)
    post_info = get_post_info(data)
    publication = PublicationView(
        publication_type=publication_info.get('publication_type'),
        file_id=publication_info.get('file_id'),
        text=publication_info.get('text'),
        button=ButtonView(
            name=publication_info.get('button').get('text'),
            url=publication_info.get('button').get('url'),
        )
    )
    try:
        for post in post_info.get("posts"):
            client.create(Endpoint.POST, PostView(
                publication=publication,
                group_id=post_info.get('group_id'),
                with_pin=post.get('with_pin'),
                publish_date=post.get('date'),
                publish_time=post.get('time')
            ).to_dict())

    except Exception as ex:
        return await message.answer(str(ex))

    await add_post(session, post_info.get('group_id'), post_info.get('total_price'))
    await message.answer("Объявление создано", reply_markup=main_kb_by_role(message))
    await state.clear()


@router.message(F.text.lower().contains("статистика"))
@router.message(Statistic.subject, F.text.lower().contains("назад"))
async def statistic_handler(message: Message, session: AsyncSession, state: FSMContext):
    if not await is_vendor(session, str(message.chat.id)):
        return await default_client_handler(message)

    await message.answer("Статистика по группах", reply_markup=statistic_samples_kb())
    await state.set_state(Statistic.sample)


@router.message(Statistic.sample, F.text.lower().contains("общая"))
async def statistic_sample_all_handler(message: Message, session: AsyncSession, state: FSMContext):
    if not await is_vendor(session, str(message.chat.id)):
        return await default_client_handler(message)

    found_user = await find_user_by_telegram_id(session, str(message.chat.id))
    groups = await get_user_groups(session, found_user.id)
    if not groups:
        return await message.answer("У вас нету добавленных групп")

    total = 0
    month = 0
    week = 0
    for group in groups:
        total += await get_total_price_all_time(session, group.id)
        month += await get_total_price_last_days(session, group.id, 30)
        week += await get_total_price_last_days(session, group.id, 7)

    await message.answer(f"Общая статистика\n"
                         f"Заработано всего - {total}\n"
                         f"Заработано за месяц - {month}\n"
                         f"Заработано за неделю - {week}", reply_markup=main_kb_by_role(message))
    await state.clear()


@router.message(Statistic.sample, F.text.lower().contains("выбрать группу"))
@router.message(Statistic.city, F.text.lower().contains("назад"))
async def statistic_sample_one_handler(message: Message, session: AsyncSession, state: FSMContext):
    if not await is_vendor(session, str(message.chat.id)):
        return await default_client_handler(message)

    found_user = await find_user_by_telegram_id(session, str(message.chat.id))
    client = ApiClient(found_user)
    groups = await get_user_groups(session, found_user.id)
    if not groups:
        return await message.answer("У вас нету добавленных групп")

    subjects_dict = {}
    cities = {}
    for group in groups:
        try:
            subject = client.get_by_id(Endpoint.SUBJECT, group.subject_id)
            if subject.get("id") not in subjects_dict:
                subjects_dict[subject.get("id")] = subject.get("name")

            if subject.get("id") in cities:
                cities[subject.get("id")].append(group.city_id)

            else:
                cities[subject.get("id")] = [group.city_id]

        except Exception as ex:
            await message.answer(str(ex))

    subjects = []
    for key, value in subjects_dict.items():
        subjects.append(
            {
                "id": key,
                "name": value
            }
        )
    if await state.get_state() == Statistic.sample:
        await message.answer("Статистика по выбранной группе", reply_markup=back_kb())

    await state.update_data(cities=cities)
    await message.answer("Выберите направление", reply_markup=subjects_kb(subjects))
    await state.set_state(Statistic.subject)


@router.callback_query(Statistic.subject, SubjectCbData.filter())
async def statistic_city_handler(callback: CallbackQuery, callback_data: SubjectCbData, session: AsyncSession,
                                 state: FSMContext):
    if not await is_vendor(session, str(callback.message.chat.id)):
        return await default_client_handler(callback.message)

    await state.update_data(subject_id=callback_data.subject_id)
    found_user = await find_user_by_telegram_id(session, str(callback.message.chat.id))
    client = ApiClient(found_user)
    data = await state.get_data()
    try:
        response = client.get_all(Endpoint.CITY, {"ids": data["cities"][callback_data.subject_id]})
        cities = response.get("responseList")
        if not cities:
            return await callback.answer("Города не добавлены")

        await callback.message.edit_text(
            text="Выберите город",
            reply_markup=cities_kb(cities)
        )
        await state.set_state(Statistic.city)

    except Exception as ex:
        await callback.answer(str(ex))


@router.callback_query(Statistic.city, CityCbData.filter())
async def statistic_groups_handler(callback: CallbackQuery, callback_data: CityCbData, session: AsyncSession,
                                   state: FSMContext):
    if not await is_vendor(session, str(callback.message.chat.id)):
        return await default_client_handler(callback.message)

    await state.update_data(city_id=callback_data.city_id)
    found_user = await find_user_by_telegram_id(session, str(callback.message.chat.id))
    client = ApiClient(found_user)
    try:
        response = client.get_all(Endpoint.GROUP, {
            "cityId": callback_data.city_id,
            "userTelegramId": callback.message.chat.id
        })
        groups = response.get("responseList")
        await callback.message.edit_text(
            text="Выберите группу",
            reply_markup=all_groups_kb(groups)
        )
        await state.set_state(Statistic.group)

    except Exception as ex:
        await callback.answer(str(ex))


@router.message(Statistic.group, F.text.lower().contains("назад"))
async def statistic_groups_back_handler(message: Message, session: AsyncSession, state: FSMContext):
    if not await is_vendor(session, str(message.chat.id)):
        return await default_client_handler(message)

    data = await state.get_data()
    found_user = await find_user_by_telegram_id(session, str(message.chat.id))
    client = ApiClient(found_user)
    try:
        response = client.get_all(Endpoint.CITY, {"ids": data["cities"][data["subject_id"]]})
        cities = response.get("responseList")
        if not cities:
            return await message.answer("Города не добавлены")

        await message.answer(
            text="Выберите город",
            reply_markup=cities_kb(cities)
        )
        await state.set_state(Statistic.city)

    except Exception as ex:
        await message.answer(str(ex))


@router.callback_query(Statistic.group, GroupCbData.filter())
async def statistic_group_handler(callback: CallbackQuery, callback_data: GroupCbData, session: AsyncSession,
                                  state: FSMContext):
    if not await is_vendor(session, str(callback.message.chat.id)):
        return await default_client_handler(callback.message)

    await state.update_data(group_id=callback_data.group_id)
    found_user = await find_user_by_telegram_id(session, str(callback.message.chat.id))
    client = ApiClient(found_user)
    try:
        group = client.get_by_id(Endpoint.GROUP, callback_data.group_id)
        schedule = client.get_by_id(Endpoint.SCHEDULE, callback_data.group_id)
        times_in_day = len(schedule.get("weeks")[0].get("days")[0].get("times"))
        posts_total_count = 0
        for i in range(1, 8):
            date = datetime.now() - timedelta(days=i)
            posts = client.get_all(Endpoint.POST, {"publishDate": date.date().strftime("%Y-%m-%d")})
            posts_total_count += posts.get("total")

    except Exception as ex:
        return await callback.answer(str(ex))

    group_local = await get_group_by_telegram_id_and_user_telegram_id(session,
                                                                      group["groupTelegramId"],
                                                                      str(callback.message.chat.id))

    total = await get_total_price_all_time(session, group_local.id)
    month = await get_total_price_last_days(session, group_local.id, 30)
    week = await get_total_price_last_days(session, group_local.id, 7)

    await callback.message.edit_text(text=f"Статистика группы <b>{group['name']}</b>\n"
                                          f"Заработано всего - {total}\n"
                                          f"Заработано за месяц - {month}\n"
                                          f"Заработано за неделю - {week}\n"
                                          f"Процент покрытия закрытых объявлений - "
                                          f"{int(posts_total_count*100/times_in_day)}%", parse_mode=ParseMode.HTML)

    await callback.message.answer("Главное меню", reply_markup=main_kb_by_role(callback.message))
    await state.clear()


@router.message()
async def unknown_handler(message: Message, session: AsyncSession):
    if not await is_vendor(session, str(message.chat.id)):
        return await default_client_handler(message)

    await message.answer("Неизвестная команда", reply_markup=main_kb_by_role(message))


@router.callback_query()
async def unknown_callback(callback: CallbackQuery):
    await callback.answer()
