class ValidationException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class NoSuchEntityException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class InternalServerError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class BadRequestException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class ForbiddenException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)
