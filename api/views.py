import datetime

from api.enums import PublicationType, PostStatus


class SubjectView:
    def __init__(self, name: str, _id: int = None):
        self.id = _id
        self.name = name

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name
        }


class CityView:
    def __init__(self, name: str, subject_id: id = None, _id: int = None):
        self.id = _id
        self.name = name
        self.subject_id = subject_id

    def to_dict(self):
        data = {
            "id": self.id,
            "name": self.name,
            "subjectId": self.subject_id
        }
        if not self.subject_id:
            del data["subjectId"]

        return data


class UserView:
    def __init__(self, telegram_id: str, _id: int = None):
        self.id = _id
        self.telegram_id = telegram_id

    def to_dict(self):
        return {
            "id": self.id,
            "telegramId": self.telegram_id
        }


class PriceView:
    def __init__(self, without_pin: int, with_pin: int):
        self.without_pin = without_pin
        self.with_pin = with_pin

    def to_dict(self):
        return {
            "withoutPin": self.without_pin,
            "withPin": self.with_pin
        }


class GroupView:
    def __init__(self, name: str, group_telegram_id: str, user_telegram_id: str, city_id: int,
                 price_for_one_day: PriceView,
                 price_for_one_week: PriceView,
                 price_for_two_weeks: PriceView, price_for_one_month: PriceView,
                 working_hours_start: str = "00:00", working_hours_end: str = "24:00",
                 post_interval_in_minutes: int = 60, link: str = None, _id: int = None):
        self.id = _id
        self.name = name
        self.group_telegram_id = group_telegram_id
        self.user_telegram_id = user_telegram_id
        self.city_id = city_id
        self.working_hours_start = working_hours_start
        self.working_hours_end = working_hours_end
        self.post_interval_in_minutes = post_interval_in_minutes
        self.link = link
        self.price_for_one_day = price_for_one_day.to_dict()
        self.price_for_one_week = price_for_one_week.to_dict()
        self.price_for_two_weeks = price_for_two_weeks.to_dict()
        self.price_for_one_month = price_for_one_month.to_dict()

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "groupTelegramId": self.group_telegram_id,
            "userTelegramId": self.user_telegram_id,
            "cityId": self.city_id,
            "workingHoursStart": self.working_hours_start,
            "workingHoursEnd": self.working_hours_end,
            "postIntervalInMinutes": self.post_interval_in_minutes,
            "link": self.link,
            "priceForOneDay": self.price_for_one_day,
            "priceForOneWeek": self.price_for_one_week,
            "priceForTwoWeeks": self.price_for_two_weeks,
            "priceForOneMonth": self.price_for_one_month
        }


class ButtonView:
    def __init__(self, name: str, url: str):
        self.name = name
        self.url = url

    def to_dict(self):
        return {
            "name": self.name,
            "url": self.url
        }


class PublicationView:
    def __init__(self, publication_type: PublicationType, file_id: int = None, text: str = None,
                 button: ButtonView = None):
        self.publication_type = publication_type
        self.file_id = file_id
        self.text = text
        self.button = button

    def to_dict(self):
        return {
            "type": self.publication_type.value,
            "fileId": self.file_id,
            "text": self.text,
            "button": self.button.to_dict()
        }


class PostView:
    def __init__(self, publication: PublicationView, group_id: int, with_pin: bool,
                 publish_date: datetime.date, publish_time: datetime.time, message_id: int,
                 _id: int = None, status: PostStatus = PostStatus.AWAITS):
        self.id = _id
        self.publication = publication
        self.group_id = group_id
        self.with_pin = with_pin
        self.publish_date = publish_date
        self.publish_time = publish_time
        self.status = status
        self.message_id = message_id

    def to_dict(self):
        return {
            "id": self.id,
            "publication": self.publication.to_dict(),
            "groupId": self.group_id,
            "withPin": self.with_pin,
            "publishDate": self.publish_date.strftime("%Y-%m-%d"),
            "publishTime": self.publish_time.strftime("%H:%M"),
            "status": self.status.value,
            "messageId": self.message_id
        }
