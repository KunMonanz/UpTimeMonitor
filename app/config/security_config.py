import bcrypt

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against a hashed value."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def dummy_hash_password() -> str:
    """Generate a dummy hashed password for testing purposes."""
    password = "DUMMY_PASSWORD"
    return hash_password(password)