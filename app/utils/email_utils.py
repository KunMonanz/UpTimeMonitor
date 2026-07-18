from email_validator import validate_email, EmailNotValidError

async def is_email(email: str) -> bool:
    try:
        email_info = validate_email(email, check_deliverability=False)
        return True
    except EmailNotValidError:
        return False
        