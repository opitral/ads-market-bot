class SubjectView:
    def __init__(self, name, _id=None):
        self.id = _id
        self.name = name

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name
        }


class CityView:
    def __init__(self, city, subject_id, _id=None):
        self.id = _id
        self.city = city
        self.subject_id = subject_id

    def to_dict(self):
        return {
            "id": self.id,
            "city": self.city,
        }


class UserView:
    def __init__(self, telegram_id, _id=None):
        self.id = _id
        self.telegram_id = telegram_id

    def to_dict(self):
        return {
            "id": self.id,
            "telegramId": self.telegram_id
        }


class PriceView:
    def __init__(self, without_pin, with_pin):
        self.without_pin = without_pin
        self.with_pin = with_pin

    def to_dict(self):
        return {
            "withPin": self.with_pin,
            "withoutPin": self.without_pin
        }


class GroupView:
    def __init__(self, name, group_telegram_id, user_telegram_id, city_id, price_for_one_day: PriceView,
                 price_for_one_week: PriceView,
                 price_for_two_weeks: PriceView, price_for_one_month: PriceView,
                 working_hours_start="00:00", working_hours_end="24:00",
                 post_interval_in_minutes=60, link=None, _id=None):
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
    def __init__(self, text, url):
        self.text = text
        self.url = url

    def to_dict(self):
        return {
            "text": self.text,
            "url": self.url
        }


class PublicationView:
    def __init__(self, _type, file_id=None, text=None, button=None):
        self.type = _type
        self.file_id = file_id
        self.text = text
        self.button = button

    def to_dict(self):
        return {
            "type": self.type,
            "fileId": self.file_id,
            "text": self.text,
            "button": self.button
        }


class PostView:
    def __init__(self, publication, group_id, publish_date, publish_time, _id=None):
        self.id = _id
        self.publication = publication
        self.group_id = group_id
        self.publish_date = publish_date
        self.publish_time = publish_time

    def to_dict(self):
        return {
            "id": self.id,
            "publication": self.publication,
            "groupId": self.group_id,
            "publishDate": self.publish_date,
            "publishTime": self.publish_time
        }
