"""One recipient budget for workflow email nodes and managed channel sends."""
from ..core import config
from ..core.errors import AppError
from .rate_limit import throttled


def take_email_quota(counter, uid, recipients):
    if counter is None: return
    limit = config.email_node_hourly_limit()
    count, retry = counter.add(f"email:{uid}", recipients, 3600)
    if count > limit:
        throttled("email_node"); raise AppError("EMAIL_RATE_LIMITED", limit=limit, retry=retry)
