#!/usr/bin/env bash
# Create .venv and install VetStats 2.0 dependencies (one-time setup).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v python3 >/dev/null 2>&1; then
  echo "VetStats 2.0: nie znaleziono python3 w PATH." >&2
  echo "Zainstaluj Python 3.10 lub nowszy, a następnie uruchom ten skrypt ponownie." >&2
  exit 127
fi

if [[ ! -d "$ROOT/.venv" ]]; then
  echo "Tworzenie środowiska wirtualnego w $ROOT/.venv ..."
  python3 -m venv "$ROOT/.venv"
fi

VENV_PYTHON="$ROOT/.venv/bin/python"
VENV_PIP="$ROOT/.venv/bin/pip"

echo "Instalowanie zależności projektu ..."
"$VENV_PIP" install --upgrade pip
"$VENV_PIP" install -e "$ROOT"

echo ""
echo "Konfiguracja zakończona."
echo "Uruchom aplikację z ikony na Pulpicie (po jednorazowym buildzie skrótu):"
echo "  \"$ROOT/scripts/build_macos_launcher.sh\""
echo "lub bezpośrednio:"
echo "  \"$ROOT/run_vetstats.command\""
echo "lub:"
echo "  \"$ROOT/scripts/run_vetstats.sh\""
