from pathlib import Path
import secrets

print(secrets.token_hex(32))
print(Path(__file__).parent)