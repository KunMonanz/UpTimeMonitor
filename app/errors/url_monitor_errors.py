class URLMonitorError(Exception):
    pass


class URLMonitorDoesNotExist(URLMonitorError):
    def __init__(self, message, status_code=404):
        super().__init__(message)
        self.status_code = status_code


class DuplicateURLMonitorForOwner(URLMonitorError):
    def __init__(self, message="A monitor for this URL already exists for this owner"):
        super().__init__(message)
