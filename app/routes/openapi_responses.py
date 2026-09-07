from app.schemas.error_schema import ErrorResponse

BAD_REQUEST_RESPONSE = {
    400: {"model": ErrorResponse, "description": "Bad request"},
}

UNAUTHORIZED_RESPONSE = {
    401: {"model": ErrorResponse, "description": "Unauthorized"},
}

FORBIDDEN_RESPONSE = {
    403: {"model": ErrorResponse, "description": "Forbidden"},
}

NOT_FOUND_RESPONSE = {
    404: {"model": ErrorResponse, "description": "Resource not found"},
}

CONFLICT_RESPONSE = {
    409: {"model": ErrorResponse, "description": "Conflict"},
}

TOO_MANY_REQUESTS_RESPONSE = {
    429: {
        "model": ErrorResponse,
        "description": "Too many requests",
        "headers": {
            "Retry-After": {
                "description": "Seconds until the request can be retried",
                "schema": {"type": "string"},
            }
        },
    },
}
