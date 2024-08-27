import math
from typing import List

from aiogram.filters.callback_data import CallbackData
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

from config_reader import config
from database.models import User


def main_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()

    kb.button(text="✏️ Создать объявление")
    kb.button(text="💬 Мои группы")
    kb.button(text="📊 Статистика")
    kb.button(text="🆕 Добавить группу")
    kb.button(text="🌟 Админка")

    kb.adjust(2, 2, 1)
    return kb.as_markup(resize_keyboard=True)


def administration_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()

    kb.button(text="👤 Пользователи")
    kb.button(text="🗺 Направления и города")
    kb.button(text="🏠 В главное меню")

    kb.adjust(2, 1)
    return kb.as_markup(resize_keyboard=True)


class UserInfoCbData(CallbackData, prefix="user_info"):
    user_id: int


class PaginationCbData(CallbackData, prefix="pagination"):
    page: int


def all_users_kb(users: List[User], page: int = 0) -> InlineKeyboardMarkup:
    limit = config.PAGE_LIMIT
    start_offset = page * limit
    end_offset = start_offset + limit
    index = 1

    kb = InlineKeyboardBuilder()

    for user in users[start_offset:end_offset]:
        kb.row(InlineKeyboardButton(
            text=f"{start_offset + index}. {user.username}",
            callback_data=UserInfoCbData(user_id=user.id).pack()
        ))
        index += 1

    pages_count = math.ceil(len(users) / limit)
    previous_page = (page - 1) if page > 0 else pages_count - 1
    next_page = (page + 1) if end_offset < len(users) else 0

    pagination_buttons = [
        InlineKeyboardButton(text="⬅️", callback_data=PaginationCbData(page=previous_page).pack()),
        InlineKeyboardButton(text=f"{page+1}/{pages_count}", callback_data="none"),
        InlineKeyboardButton(text="➡️", callback_data=PaginationCbData(page=next_page).pack())
    ]

    kb.row(*pagination_buttons)

    return kb.as_markup()


class UserAllowedChatsChangeCbData(CallbackData, prefix="user_allowed_chats_change"):
    user_id: int
    value: int


class UserRoleChangeCbData(CallbackData, prefix="user_role_change"):
    user_id: int


def user_settings_kb(user_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()

    kb.button(text="-1 💬", callback_data=UserAllowedChatsChangeCbData(
        user_id=user_id,
        value=-1
    ))
    kb.button(text="+1 💬", callback_data=UserAllowedChatsChangeCbData(
        user_id=user_id,
        value=1
    ))
    kb.button(text="🔄 Изменить роль", callback_data=UserRoleChangeCbData(user_id=user_id))

    kb.adjust(2, 1)
    return kb.as_markup()


class SubjectCbData(CallbackData, prefix="subject"):
    subject_id: int


def all_subjects_kb(subjects: List[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for subject in subjects:
        kb.row(InlineKeyboardButton(text=subject.get("name"),
                                    callback_data=SubjectCbData(subject_id=subject.get("id")).pack()))

    return kb.as_markup()


class CitiesCbData(CallbackData, prefix="cities"):
    subject_id: int


class SubjectNameChangeCbData(CallbackData, prefix="subject_name_change"):
    subject_id: int


def subject_kb(subject_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()

    kb.button(text="Изменить название", callback_data=SubjectNameChangeCbData(subject_id=subject_id).pack())
    kb.button(text="Города", callback_data=CitiesCbData(subject_id=subject_id).pack())

    kb.adjust(1)
    return kb.as_markup()
