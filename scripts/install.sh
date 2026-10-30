#!/bin/sh
# Install the superstep command.
#   curl -fsSL https://raw.githubusercontent.com/quinguyen1502/superstep/develop/scripts/install.sh | sh
# Native Windows is refused (use WSL). When uv is missing, this installs uv, then
# `uv tool install 'superstep[cli]==<version>'`. SUPERSTEP_VERSION overrides the pin.
set -eu

VERSION="${SUPERSTEP_VERSION:-0.10.0}"

os_name=$(uname -s 2>/dev/null || printf '%s' "${OS:-unknown}")
case "$os_name" in
  MINGW*|MSYS*|CYGWIN*|Windows_NT)
    echo "Superstep's command line does not install on native Windows. Use WSL." >&2
    exit 1
    ;;
esac

if ! command -v uv >/dev/null 2>&1; then
  url="${SUPERSTEP_UV_INSTALL_URL:-https://astral.sh/uv/install.sh}"
  curl -LsSf "$url" | sh
  if [ -x "${HOME}/.local/bin/uv" ]; then
    PATH="${HOME}/.local/bin:${PATH}"
    export PATH
  fi
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is not on PATH." >&2
  exit 1
fi

uv tool install "superstep[cli]==${VERSION}"

if ! command -v superstep >/dev/null 2>&1 && [ -x "${HOME}/.local/bin/superstep" ]; then
  PATH="${HOME}/.local/bin:${PATH}"
  export PATH
fi

if ! command -v superstep >/dev/null 2>&1; then
  echo "superstep is installed but not on PATH. Add ${HOME}/.local/bin to PATH." >&2
  exit 1
fi

echo "superstep ${VERSION} is on PATH (also as sstep)." >&2
