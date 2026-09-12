from cryptography.fernet import Fernet, InvalidToken

from backend.app.settings import settings


class SecretCipher:
    def __init__(self, key: str | None = None):
        material = key or settings.api_encryption_key
        if not material:
            raise RuntimeError("API_ENCRYPTION_KEY مطلوب؛ لا يمكن حفظ مفاتيح التداول بدون تشفير.")
        self._fernet = Fernet(material.encode())

    def encrypt(self, value: str) -> str:
        return self._fernet.encrypt(value.encode()).decode()

    def decrypt(self, value: str) -> str:
        try:
            return self._fernet.decrypt(value.encode()).decode()
        except InvalidToken as error:
            raise ValueError("تعذر فك تشفير السر المخزن") from error
