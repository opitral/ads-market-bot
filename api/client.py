import json
import random
import string
import requests

from database.models import User, Role
from api.enums import Endpoint, Method
from api.exceptions import ValidationException, NoSuchEntityException, InternalServerError, BadRequestException, \
    ForbiddenException


class ApiClient:
    def __init__(self, user: User):
        self.user = user

    def permit(self, endpoint: Endpoint, method: Method):
        client_permissions = {
            Endpoint.USER: [Method.POST]
        }

        vendor_permissions = {
            Endpoint.SUBJECT: [Method.GET],
            Endpoint.CITY: [Method.GET],
            Endpoint.GROUP: [Method.GET, Method.POST],
            Endpoint.USER: [Method.POST],
            Endpoint.POST: [Method.POST],
        }

        if self.user.role == Role.ADMIN:
            return

        elif self.user.role == Role.CLIENT:
            if method not in client_permissions[endpoint]:
                raise ForbiddenException("У вас недостаточно прав")

        elif self.user.role == Role.VENDOR:
            if method not in vendor_permissions[endpoint]:
                raise ForbiddenException("У вас недостаточно прав")

    @staticmethod
    def valid(response: dict):
        error = response.get("error")
        if error:
            if error.get("code") == 409:
                raise ValidationException(error.get("errors")[0])

            elif error.get("code") == 404:
                raise NoSuchEntityException(error.get("message"))

            elif error.get("code") == 400:
                raise BadRequestException(error.get("message"))

            elif error.get("code") == 500:
                raise InternalServerError("Internal Server Error")

    @staticmethod
    def get_random_string(length: int) -> str:
        letters_and_digits = string.ascii_letters + string.digits
        return "".join(random.choice(letters_and_digits) for _ in range(length))

    def create(self, endpoint: Endpoint, body: dict):
        self.permit(endpoint, Method.POST)
        response = json.loads(requests.post(endpoint.value, json=body).text)
        self.valid(response)
        return response.get("result")

    def update(self, endpoint: Endpoint, body: dict):
        self.permit(endpoint, Method.PUT)
        response = json.loads(requests.put(endpoint.value, json=body).text)
        self.valid(response)
        return response.get("result")

    def delete(self, endpoint: Endpoint, _id: int):
        self.permit(endpoint, Method.DELETE)
        response = json.loads(requests.delete(f"{endpoint.value}/{_id}").text)
        self.valid(response)
        return response.get("result")

    def get_by_id(self, endpoint: Endpoint, _id: int):
        self.permit(endpoint, Method.GET)
        response = json.loads(requests.get(f"{endpoint.value}/{_id}").text)
        self.valid(response)
        return response.get("result")

    def get_all(self, endpoint: Endpoint, restrict: dict = None):
        self.permit(endpoint, Method.GET)

        if restrict is None:
            restrict = {}

        response = json.loads(
            requests.get(endpoint.value, params={"restrict": json.dumps(restrict)}).text
        )
        self.valid(response)
        return response.get("result")
