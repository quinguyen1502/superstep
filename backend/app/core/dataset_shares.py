import re

DATASET_SHARE_PREFIX = "dssh_"
DATASET_SHARE_TOKEN = re.compile(DATASET_SHARE_PREFIX + r"[A-Za-z0-9_-]{43}")
