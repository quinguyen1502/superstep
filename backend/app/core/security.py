"""Security primitives: password hashing (PBKDF2), JWT issue/verify, secret and password policy checks."""
import hashlib, hmac, re, secrets, time
import jwt
from . import config
from .errors import AppError
from .logging import get_logger

log = get_logger("auth")
PLACEHOLDER_SECRET = config.PLACEHOLDER_SECRET
SECRET = config.JWT_SECRET
TTL = config.JWT_TTL_SECONDS
ITER = 200_000
IS_PROD = config.IS_PROD

def check_secret():
    """Refuse the placeholder secret in production; warn in dev."""
    if SECRET == PLACEHOLDER_SECRET:
        if IS_PROD: raise RuntimeError("JWT_SECRET must be set when STUDIO_ENV=production")
        log.warning("JWT_SECRET is the development placeholder; set JWT_SECRET before deploying")
        return False
    return True

def password_problem(pw: str) -> AppError | None:
    """Return a user-facing message if the password is too weak, else None."""
    if len(pw) < 8: return AppError("AUTH_PASSWORD_TOO_SHORT", min=8)
    if len(pw) > 128: return AppError("AUTH_PASSWORD_TOO_LONG", max=128)
    if not re.search(r"[A-Za-z]", pw) or not re.search(r"\d", pw): return AppError("AUTH_PASSWORD_WEAK")
    return None

def hash_password(pw: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), ITER).hex()
    return f"pbkdf2_sha256${ITER}${salt}${h}"

def verify_password(pw: str, stored: str) -> bool:
    try:
        _, it, salt, h = stored.split("$")
        return hmac.compare_digest(hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), int(it)).hex(), h)
    except Exception:
        return False

SESSION_COOKIE = "studio_session"  # HttpOnly cookie that carries the JWT for the browser UI
CSRF_HEADER, CSRF_VALUE = "x-requested-with", "studio"  # cookie-authenticated writes must send it


def make_token(uid: str, email: str, ttl: int | None = None) -> str:
    now = int(time.time())
    return jwt.encode({"sub": uid, "email": email, "iat": now, "exp": now + (TTL if ttl is None else ttl)}, SECRET, algorithm="HS256")

def decode_token(tok: str) -> dict:
    """Return the JWT payload or raise Unauthorized (expired: AUTH_TOKEN_EXPIRED + header X-Auth-Error: expired)."""
    try:
        return jwt.decode(tok, SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise AppError("AUTH_TOKEN_EXPIRED", headers={"X-Auth-Error": "expired"})
    except jwt.PyJWTError:
        raise AppError("AUTH_TOKEN_INVALID")
