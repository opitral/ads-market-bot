from typing import List

from aiogram.filters.callback_data import CallbackData
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButtonRequestChat
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


def main_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()

    kb.button(text="✏️ Создать объявление")
    kb.button(text="💬 Мои группы")
    kb.button(text="📊 Статистика")
    kb.button(text="🆕 Добавить группу")

    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)


def cancel_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="Отменить")
    return kb.as_markup(resize_keyboard=True)


class SubjectCbData(CallbackData, prefix="group_subject"):
    subject_id: int


def subjects_kb(subjects: List[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for subject in subjects:
        kb.row(InlineKeyboardButton(text=subject.get("name"),
                                    callback_data=SubjectCbData(subject_id=subject.get("id")).pack()))

    return kb.as_markup()


class CityCbData(CallbackData, prefix="group_city"):
    city_id: int


def cities_kb(cities: List[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for city in cities:
        kb.row(InlineKeyboardButton(text=city.get("name"), callback_data=CityCbData(city_id=city.get("id")).pack()))

    return kb.as_markup()


def back_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="Назад")
    return kb.as_markup(resize_keyboard=True)


def group_choose_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(
        text="Выбрать группу",
        request_chat=KeyboardButtonRequestChat(
            request_id=1,
            chat_is_channel=False,
            chat_is_created=True,
            request_title=True,
            request_username=True
        )
    )
    kb.button(text="Назад")
    kb.adjust(1)
    return kb.as_markup(resize_keyboard=True)


class GroupCbData(CallbackData, prefix="user_group"):
    group_id: int


def all_groups_kb(groups: List[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for group in groups:
        kb.row(InlineKeyboardButton(text=group.get("name"), callback_data=GroupCbData(group_id=group.get("id")).pack()))

    return kb.as_markup()


class GroupWorkTimesCbData(CallbackData, prefix="group_work_times"):
    group_id: int


class GroupPostsIntervalCbData(CallbackData, prefix="group_posts_interval"):
    group_id: int


class GroupPriceListCbData(CallbackData, prefix="group_price_list"):
    group_id: int


class GroupDeleteCbData(CallbackData, prefix="group_delete"):
    group_id: int


def group_kb(group_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="Время работы", callback_data=GroupWorkTimesCbData(group_id=group_id).pack()))
    kb.row(InlineKeyboardButton(text="Интервал публикаций", callback_data=GroupPostsIntervalCbData(group_id=group_id).pack()))
    kb.row(InlineKeyboardButton(text="Прайс лист", callback_data=GroupPriceListCbData(group_id=group_id).pack()))
    kb.row(InlineKeyboardButton(text="Удалить", callback_data=GroupDeleteCbData(group_id=group_id).pack()))
    return kb.as_markup()


class GroupDeleteSubmitCbData(CallbackData, prefix="group_submit_delete"):
    group_id: int


class GroupDeleteCancelCbData(CallbackData, prefix="group_cancel_delete"):
    group_id: int


def submit_delete_kb(group_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="Подтвердить", callback_data=GroupDeleteSubmitCbData(group_id=group_id).pack()),
           InlineKeyboardButton(text="Отменить", callback_data=GroupDeleteCancelCbData(group_id=group_id).pack()))
    return kb.as_markup()
