#!/bin/sh
# Install the OpenTelemetry SDK into the persistent tool cache for the
# current interpreter. Pins live only in this file.
#
#   scripts/otel_setup.sh
#   PFY_TOOL_CACHE=./tmp/toolcache scripts/otel_setup.sh
#
# Target: ${PFY_TOOL_CACHE:-$HOME/.cache/pfy}/tools/otel/site-py<major><minor>
# Does not touch the LiteLLM venv. Does not start Phoenix.
set -eu

# Pins (one place).
SDK_PIN="opentelemetry-sdk==1.45.2"
HTTP_PIN="opentelemetry-exporter-otlp-proto-http==1.45.2"
SEMCONV_PIN="openinference-semantic-conventions==0.1.44"

cache="${PFY_TOOL_CACHE:-$HOME/.cache/pfy}"
case "$cache" in
  /*) ;;
  *) cache=$(CDPATH= cd -- "$cache" && pwd) ;;
esac
py=$(python3 -c 'import sys; print("%d%d" % (sys.version_info[0], sys.version_info[1]))')
dest="$cache/tools/otel/site-py$py"
mkdir -p "$dest"
uv pip install --python python3 --target "$dest" \
  "$SDK_PIN" \
  "$HTTP_PIN" \
  "$SEMCONV_PIN"
echo "otel site $dest"
