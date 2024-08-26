from aiogram.filters import BaseFilter
from aiogram.types import Message

from config_reader import config


class ChatTypeFilter(BaseFilter):
    def __init__(self, is_group: bool):
        self.is_group = is_group

    async def __call__(self, message: Message) -> bool:
        return message.chat.type in ["group", "supergroup"] if self.is_group else message.chat.type == "private"


class IsAdminFilter(BaseFilter):
    def __init__(self) -> None:
        self.admin_ids = config.ADMIN_TELEGRAM_IDS

    async def __call__(self, message: Message) -> bool:
        return message.from_user.id in self.admin_ids
