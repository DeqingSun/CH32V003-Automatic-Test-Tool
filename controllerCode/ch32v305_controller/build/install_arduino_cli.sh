#!/usr/bin/env bash
set -euo pipefail

script_dir="$(
  cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1
  pwd -P
)"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "ERROR: This installer currently supports macOS only." >&2
  exit 1
fi

arch="$(uname -m)"
if [[ "$arch" != "arm64" ]]; then
  echo "ERROR: This script is for macOS ARM64 (Apple Silicon). Detected: $arch" >&2
  exit 1
fi

install_dir="${script_dir}/arduino_cli"
bin_dir="${install_dir}/bin"
cli_path="${bin_dir}/arduino-cli"

url="https://downloads.arduino.cc/arduino-cli/arduino-cli_latest_macOS_ARM64.tar.gz"

mkdir -p "$bin_dir"

if [[ -x "$cli_path" ]]; then
  echo "Arduino CLI already installed:"
  echo "  $cli_path"
  echo "Version:"
  "$cli_path" version
  exit 0
fi

tmp_dir="${install_dir}/.tmp"
mkdir -p "$tmp_dir"
tgz_path="${tmp_dir}/arduino-cli_latest_macOS_ARM64.tar.gz"

download() {
  if command -v curl >/dev/null 2>&1; then
    curl -fL --retry 3 --retry-delay 2 -o "$tgz_path" "$url"
    return 0
  fi
  if command -v wget >/dev/null 2>&1; then
    wget -O "$tgz_path" "$url"
    return 0
  fi
  echo "ERROR: Need curl or wget to download Arduino CLI." >&2
  return 1
}

extract() {
  rm -f "$cli_path"
  tar -xzf "$tgz_path" -C "$bin_dir"

  if [[ -f "$cli_path" ]]; then
    chmod +x "$cli_path" || true
    return 0
  fi

  # Fallback: if archive layout changes, find the binary and normalize the name.
  found="$(
    find "$bin_dir" -maxdepth 2 -type f -name "arduino-cli*" 2>/dev/null | head -n 1 || true
  )"
  if [[ -n "$found" && -f "$found" ]]; then
    mv -f "$found" "$cli_path"
    chmod +x "$cli_path" || true
    return 0
  fi

  echo "ERROR: Extraction succeeded but arduino-cli binary not found in ${bin_dir}." >&2
  return 1
}

echo "Installing Arduino CLI into: $install_dir"
echo "Downloading: $url"
download
echo "Extracting into: $bin_dir"
extract

echo
echo "Installed: $cli_path"
echo "Version:"
"$cli_path" version

# Share board cores, tools, and libraries with Arduino IDE (same ~/Library/Arduino15).
arduino_data_dir="${HOME}/Library/Arduino15"
"$cli_path" config set directories.data "$arduino_data_dir"
"$cli_path" config set directories.downloads "${arduino_data_dir}/staging"
"$cli_path" config set directories.user "${HOME}/Documents/Arduino"

echo
echo "Arduino CLI uses the same packages as Arduino IDE:"
echo "  ${arduino_data_dir}"
echo
echo "Installed cores:"
"$cli_path" core list | grep -E '^ID|WCH' || true

echo
echo "Build commands:"
echo "  \"${script_dir}/build.sh\" compile"
echo "  \"${script_dir}/build.sh\" upload"
echo
echo "Or add CLI to PATH:"
echo "  export PATH=\"${bin_dir}:\$PATH\""
