#!/bin/sh
# All-in-one image entrypoint. Platform volumes (Fly, Railway, Render, Zeabur) are often mounted root-owned, so the
# container starts as root only to give /data to the studio user, then drops to it for the real process.
# Started as non-root already (e.g. `--user`, Railway RAILWAY_RUN_UID): run the command as is.
set -e
if [ "$(id -u)" = 0 ]; then
  mkdir -p /data && chown -R studio:studio /data 2>/dev/null || echo "warning: cannot chown /data; it must be writable by uid 10001" >&2
  exec setpriv --reuid=studio --regid=studio --init-groups -- "$@"
fi
exec "$@"
