from aiogram.types import ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def main_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()

    kb.button(text="✏️ Создать объявление")
    kb.button(text="💬 Мои группы")
    kb.button(text="📊 Статистика")
    kb.button(text="🆕 Добавить группу")

    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)
