#!/bin/sh
set -eu

validate_target() {
  awk -v value="$2" 'BEGIN {
    if (value !~ /^[0-9]*[.]?[0-9]+$/ || value <= 0 || value >= 1) exit 1
  }' || { echo "$1 must be a number greater than 0 and less than 1" >&2; exit 1; }
}

run_target=${STUDIO_SLO_RUN_SUCCESS:-0.99}
api_target=${STUDIO_SLO_API_AVAILABILITY:-0.995}
validate_target STUDIO_SLO_RUN_SUCCESS "$run_target"
validate_target STUDIO_SLO_API_AVAILABILITY "$api_target"
sed -e "s/@RUN_TARGET@/$run_target/g" -e "s/@API_TARGET@/$api_target/g" \
  /etc/prometheus/slo-rules.yaml.in > /tmp/superstep-slo-rules.yaml
exec /bin/prometheus "$@"
