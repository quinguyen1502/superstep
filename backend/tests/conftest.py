import os, tempfile
# Isolate test data before any app module is imported.
os.environ["STUDIO_DB"] = tempfile.mktemp(suffix=".db")
os.environ["STUDIO_IMPORT_DIR"] = tempfile.mkdtemp(prefix="lgs-imports-")
os.environ.pop("OPENAI_API_KEY", None)
os.environ["STUDIO_SECRET_KEY_FILE"] = os.path.join(tempfile.mkdtemp(prefix="lgs-key-"), "secret.key")
#: the session cookie is Secure here, so the shared http://testserver clients keep testing Bearer auth only
# (httpx does not send a Secure cookie over http). Cookie tests use a client with base_url="https://testserver".
os.environ["STUDIO_COOKIE_SECURE"] = "1"
