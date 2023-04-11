class RequestError(Exception):
    """Ошибка запроса."""

    pass


class HTTPRequestError(Exception):
    """Ошибка, возвращающая код ответа от API."""

    pass


class InvalidResponseCode(Exception):
    """Не верный код ответа."""

    pass
