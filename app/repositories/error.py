class URLMonitorError(Exception):
    pass


class UserError(Exception):
    pass


class URLMonitorDoesNotExist(URLMonitorError):
    def __init__(self, message, status_code=404):
        super().__init__(message)
        self.status_code = status_code


class UserDoesNotExist(UserError):
    def __init__(self, message, status_code=404):
        super().__init__(message)
        self.status_code = status_code


class TooManyRequestsError(Exception):
    status_code: int = 429

    def __init__(self, message: str, retry_after: int | None = None):
        super().__init__(message)
        self.retry_after = retry_after