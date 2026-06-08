#!/usr/bin/env bash
set -euo pipefail

script_dir="$(
  cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1
  pwd -P
)"
project_dir="$(cd -- "${script_dir}/.." && pwd -P)"
cli_path="${script_dir}/arduino_cli/bin/arduino-cli"
build_path="${script_dir}/build_out"

# Match Arduino IDE board settings.
fqbn="WCH:ch32v:CH32V30x_EVT:pnum=CH32V305CCT6,clock=144MHz_HSE,opt=ogstd,dbg=enable_all"

usage() {
  cat <<EOF
Usage: $(basename "$0") <compile|upload|build|monitor> [options]

  compile          Build the sketch only
  upload           Build and upload via WCH-SWD (WCH-LinkE)
  build            Alias for upload
  monitor          Open serial monitor (pass --port if needed)

Environment:
  ARDUINO_PORT     Serial port for monitor (e.g. /dev/cu.usbmodemCH32V30x1)

Examples:
  $(basename "$0") compile
  $(basename "$0") upload
  ARDUINO_PORT=/dev/cu.usbmodemCH32V30x1 $(basename "$0") monitor
EOF
}

if [[ ! -x "$cli_path" ]]; then
  echo "ERROR: Arduino CLI not found. Run install_arduino_cli.sh first." >&2
  exit 1
fi

action="${1:-}"
if [[ -z "$action" ]]; then
  usage
  exit 1
fi
shift || true

port="${ARDUINO_PORT:-}"
extra_args=("$@")

compile_sketch() {
  "$cli_path" compile \
    --fqbn "$fqbn" \
    --build-path "$build_path" \
    "$project_dir"
}

upload_sketch() {
  local upload_args=(
    --fqbn "$fqbn"
    --build-path "$build_path"
    --upload
    "$project_dir"
  )
  if [[ -n "$port" ]]; then
    upload_args=(--port "$port" "${upload_args[@]}")
  fi
  "$cli_path" compile "${upload_args[@]}"
}

case "$action" in
  compile)
    compile_sketch
    ;;
  upload | build)
    upload_sketch
    ;;
  monitor)
    if [[ -z "$port" ]]; then
      echo "ERROR: Set ARDUINO_PORT or pass --port for monitor." >&2
      exit 1
    fi
    "$cli_path" monitor -p "$port" -c baudrate=115200 "${extra_args[@]}"
    ;;
  -h | --help | help)
    usage
    ;;
  *)
    echo "ERROR: Unknown action: $action" >&2
    usage
    exit 1
    ;;
esac
