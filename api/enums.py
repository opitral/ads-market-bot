from enum import Enum

from config_reader import config


class Endpoint(Enum):
    BASE_URL = config.API_BASE_URL + "/api"
    SUBJECT = f"{BASE_URL}/subject"
    CITY = f"{BASE_URL}/city"
    GROUP = f"{BASE_URL}/group"
    POST = f"{BASE_URL}/post"
    USER = f"{BASE_URL}/user"

    def __str__(self):
        return self.value


class Method(Enum):
    POST = "POST"
    GET = "GET"
    PUT = "PUT"
    DELETE = "DELETE"


class PublicationType(Enum):
    PHOTO = "PHOTO"
    VIDEO = "VIDEO"
    ANIMATION = "ANIMATION"
    TEXT = "TEXT"


class PostStatus(Enum):
    AWAITS = "AWAITS"
    PUBLISHED = "PUBLISHED"
    ERROR = "ERROR"
