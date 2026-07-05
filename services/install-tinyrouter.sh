#!/usr/bin/env bash
set -euo pipefail

GO_VERSION="${GO_VERSION:-1.26.4}"
GO_ROOT="${GO_ROOT:-$HOME/.local/go}"
LOCAL_BIN="${LOCAL_BIN:-$HOME/.local/bin}"
SRC_DIR="${TINYROUTER_SRC_DIR:-$HOME/.local/src/tinyrouter}"
REPO_URL="${TINYROUTER_REPO_URL:-https://github.com/Darkstarrd-dev/tinyrouter.git}"
GO_BIN="$GO_ROOT/bin/go"

mkdir -p "$HOME/.local/downloads" "$HOME/.local/src" "$LOCAL_BIN"

if [ ! -x "$GO_BIN" ]; then
  archive="go${GO_VERSION}.darwin-arm64.tar.gz"
  url="https://go.dev/dl/$archive"
  echo "Installing Go $GO_VERSION into $GO_ROOT"
  curl -L --fail --progress-bar -o "$HOME/.local/downloads/$archive" "$url"
  rm -rf "$GO_ROOT"
  tar -C "$HOME/.local" -xzf "$HOME/.local/downloads/$archive"
else
  echo "Using existing Go: $("$GO_BIN" version)"
fi

if [ -d "$SRC_DIR/.git" ]; then
  echo "Updating TinyRouter source: $SRC_DIR"
  git -C "$SRC_DIR" pull --ff-only
else
  echo "Cloning TinyRouter into $SRC_DIR"
  git clone "$REPO_URL" "$SRC_DIR"
fi

echo "Building TinyRouter"
(
  cd "$SRC_DIR"
  GOPROXY="${GOPROXY:-https://goproxy.cn,direct}" \
  GOSUMDB="${GOSUMDB:-sum.golang.google.cn}" \
  "$GO_BIN" build -ldflags "-s -w" -o "$LOCAL_BIN/tinyrouter" .
)

echo "TinyRouter installed: $LOCAL_BIN/tinyrouter"
"$LOCAL_BIN/tinyrouter" --help 2>&1 | sed -n '1,20p'
