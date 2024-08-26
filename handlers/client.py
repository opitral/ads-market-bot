from aiogram.types import Message, ReplyKeyboardRemove

from config_reader import config


async def default_client_handler(message: Message):
    await message.answer(config.DEFAULT_CLIENT_MESSAGE, reply_markup=ReplyKeyboardRemove())
