from cryptography.fernet import Fernet
from app.core.config import settings


_cipher = Fernet(settings.token_encryption_key.encode())


def encrypt_text(value: str | None) -> str | None:
    if not value:
        return None
    return _cipher.encrypt(value.encode()).decode()


def decrypt_text(value: str | None) -> str | None:
    if not value:
        return None
    return _cipher.decrypt(value.encode()).decode()
