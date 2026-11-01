import base64
import hashlib
import hmac
import json
import time


# Server only; user_id/name come from your authenticated application user.
def mint_chat_token(*, key_id, secret, slug, user_id, name=""):
    def b64(data):
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

    def encode(value):
        return b64(json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))

    now = int(time.time())
    header = encode({"alg": "HS256", "typ": "JWT", "kid": key_id})
    claims = encode({"iss": key_id, "aud": f"superstep-chat:{slug}",
                     "sub": user_id, "name": name, "iat": now, "exp": now + 600})
    unsigned = f"{header}.{claims}"
    signature = hmac.new(secret.encode("utf-8"), unsigned.encode("ascii"), hashlib.sha256).digest()
    return f"{unsigned}.{b64(signature)}"
