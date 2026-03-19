# app/core/security.py
import bcrypt


def hash_password(plain_password: str) -> str:
    """
    Devuelve el hash bcrypt de la contrasena en texto plano.
    Usa bcrypt directamente (compatible con bcrypt >= 4.x).
    """
    password_bytes = plain_password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Retorna True si la contrasena coincide con el hash almacenado."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False
