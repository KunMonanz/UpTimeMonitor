class GroupError(Exception):
    """Base class for group-related errors."""

    pass


class GroupDoesNotExistError(GroupError):
    """Raised when a group does not exist."""

    def __init__(self, message: str = "Group does not exist", status_code: int = 404):
        super().__init__(message)
        self.status_code = status_code


class UserNotInGroupError(GroupError):
    """Raised when a user is not part of a group."""

    def __init__(
        self, message: str = "User is not in the group", status_code: int = 403
    ):
        super().__init__(message)
        self.status_code = status_code


class UserAlreadyInGroupError(GroupError):
    """Raised when a user is already part of a group."""

    def __init__(
        self, message: str = "User is already in the group", status_code: int = 400
    ):
        super().__init__(message)
        self.status_code = status_code


class UserNotGroupAdminError(GroupError):
    """Raised when a user is not an admin of the group."""

    def __init__(
        self, message: str = "User is not an admin of the group", status_code: int = 403
    ):
        super().__init__(message)
        self.status_code = status_code


class UserNotGroupMemberError(GroupError):
    """Raised when a user is not a member of the group."""

    def __init__(
        self, message: str = "User is not a member of the group", status_code: int = 403
    ):
        super().__init__(message)
        self.status_code = status_code
