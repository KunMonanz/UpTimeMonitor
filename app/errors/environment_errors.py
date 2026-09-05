class EnvironmentVariableException(Exception):
    pass


class EnvironmentVariableMissingError(EnvironmentVariableException):
    def __init__(self, variable: str):
        message = f"{variable} has not been set in the .env file"
        super().__init__(message)
