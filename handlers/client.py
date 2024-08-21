from aiogram.types import Message, ReplyKeyboardRemove


async def client_default_handler(message: Message):
    await message.answer("Свяжитесь с @parlament_er для получения доступа", reply_markup=ReplyKeyboardRemove())
