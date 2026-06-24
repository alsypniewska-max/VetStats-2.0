#!/usr/bin/env bash
# VetStats 2.0.app entry point — always launches via scripts/run_vetstats.sh (.venv only).
set -euo pipefail

_realpath() {
  python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$1"
}

_show_error_dialog() {
  local title="$1"
  local body_file="$2"
  osascript - "$title" "$body_file" <<'APPLESCRIPT' || true
on run argv
  set dialogTitle to item 1 of argv
  set bodyFile to item 2 of argv
  set bodyText to read POSIX file bodyFile
  display dialog bodyText buttons {"OK"} default button 1 with icon stop with title dialogTitle
end run
APPLESCRIPT
}

MACOS_DIR="$(cd "$(dirname "$(_realpath "$0")")" && pwd)"
ROOT="$(cd "$MACOS_DIR/../../.." && pwd)"
RUN_SCRIPT="$ROOT/scripts/run_vetstats.sh"
SETUP_SCRIPT="$ROOT/scripts/setup_venv.sh"

err_file="$(mktemp -t vetstats_launch_err.XXXXXX)"

cleanup() {
  rm -f "$err_file"
}
trap cleanup EXIT

if [[ ! -f "$RUN_SCRIPT" ]]; then
  {
    echo "Nie znaleziono skryptu uruchomieniowego VetStats."
    echo ""
    echo "Oczekiwana lokalizacja projektu:"
    echo "  $ROOT"
    echo ""
    echo "Uruchom ponownie instalator skrótu:"
    echo "  $ROOT/scripts/build_macos_launcher.sh"
  } >"$err_file"
  _show_error_dialog "VetStats 2.0" "$err_file"
  exit 1
fi

if ! "$RUN_SCRIPT" 2>"$err_file"; then
  status=$?
  {
    cat "$err_file"
    echo ""
    echo "Konfiguracja środowiska (jednorazowo):"
    echo "  $SETUP_SCRIPT"
    echo ""
    echo "Następnie uruchom ponownie VetStats z ikony na Pulpicie."
  } >"${err_file}.full"
  mv "${err_file}.full" "$err_file"
  _show_error_dialog "VetStats 2.0 — błąd uruchomienia" "$err_file"
  exit "$status"
fi
