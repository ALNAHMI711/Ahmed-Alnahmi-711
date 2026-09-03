from cryptography.fernet import Fernet
import os

KEY = os.getenv('ENCRYPTION_KEY')
if not KEY:
    raise RuntimeError('ENCRYPTION_KEY is not set in environment')

fernet = Fernet(KEY.encode() if isinstance(KEY, str) else KEY)

def encrypt_secret(plain: str) -> str:
    return fernet.encrypt(plain.encode()).decode()

def decrypt_secret(token: str) -> str:
    return fernet.decrypt(token.encode()).decode()
