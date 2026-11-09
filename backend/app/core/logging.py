"""Logger helper so modules share the `studio.*` namespace, and token redaction for uvicorn's logs."""
import logging
import re

TOKEN_RE = re.compile(r"(token=)[^&\s\"']+")


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"studio.{name}")


def redact(text: str) -> str:
    return TOKEN_RE.sub(r"\1***", text)


class RedactTokens(logging.Filter):
    """Hide `token=` query values (the WebSocket JWT) in access and connection log lines."""
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str): record.msg = redact(record.msg)
        if isinstance(record.args, tuple): record.args = tuple(redact(a) if isinstance(a, str) else a for a in record.args)
        return True


def redact_tokens(*names: str) -> None:
    for n in names:
        lg = logging.getLogger(n)
        if not any(isinstance(f, RedactTokens) for f in lg.filters): lg.addFilter(RedactTokens())
