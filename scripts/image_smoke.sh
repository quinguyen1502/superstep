#!/usr/bin/env sh
# Smoke test for the all-in-one image (CI: .github/workflows/image.yml). Usage: scripts/image_smoke.sh <base url> <container>
# Waits for /api/health, checks that the UI is served on the same origin, then runs compose_smoke.py
# (sign-in with SMOKE_EMAIL / SMOKE_PASSWORD, seeded example over /ws/run, API trigger).
set -eu
BASE=$1 NAME=$2
i=0
until curl -fsS "$BASE/api/health" >/dev/null 2>&1; do
  i=$((i + 1)); [ "$i" -gt 90 ] && { docker logs "$NAME"; echo "not healthy after 90 s" >&2; exit 1; }
  sleep 1
done
curl -fsS "$BASE/" | grep -q '<div id="root"' || { echo "UI not served at /" >&2; exit 1; }
curl -fsS "$BASE/workflows/some-route" | grep -q '<div id="root"' || { echo "SPA fallback missing" >&2; exit 1; }
[ "$(curl -s -o /dev/null -w '%{http_code}' "$BASE/api/nope")" = 404 ] || { echo "unknown /api path is not a 404" >&2; exit 1; }
docker exec "$NAME" python -c "import boto3" || { echo "boto3 (the s3 attachment backend) is missing from the image" >&2; exit 1; }  # TASK-0193
python scripts/compose_smoke.py "$BASE"
