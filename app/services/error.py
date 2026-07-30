class TokenError(Exception):
    pass


class BlacklistedTokenError(TokenError):
    pass