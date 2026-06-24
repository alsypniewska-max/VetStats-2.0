#!/usr/bin/env bash
# Build VetStats 2.0.app (clickable launcher with icon) and install a Desktop shortcut.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_NAME="VetStats 2.0"
BUNDLE_ID="pl.vetstats.vetstats2"
APP_BUNDLE="$ROOT/$APP_NAME.app"
LOGO_PNG="$ROOT/assets/branding/vetstats_logo.png"
LAUNCHER_SRC="$ROOT/scripts/macos_launcher_executable.sh"
DESKTOP_LINK="$HOME/Desktop/$APP_NAME.app"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "Ten skrypt działa tylko na macOS." >&2
  exit 1
fi

if [[ ! -f "$LOGO_PNG" ]]; then
  echo "Brak pliku ikony: $LOGO_PNG" >&2
  exit 1
fi

if [[ ! -f "$LAUNCHER_SRC" ]]; then
  echo "Brak skryptu uruchomieniowego: $LAUNCHER_SRC" >&2
  exit 1
fi

echo "Budowanie $APP_NAME.app w:"
echo "  $APP_BUNDLE"

ICONSET_DIR="$(mktemp -d -t vetstats_iconset.XXXXXX)"
ICONSET_PATH="${ICONSET_DIR}.iconset"
mv "$ICONSET_DIR" "$ICONSET_PATH"
ICONSET_DIR="$ICONSET_PATH"
cleanup() {
  rm -rf "$ICONSET_DIR"
}
trap cleanup EXIT

_make_icon() {
  local size="$1"
  local name="$2"
  sips -z "$size" "$size" "$LOGO_PNG" --out "$ICONSET_DIR/$name" >/dev/null
}

_make_icon 16 icon_16x16.png
_make_icon 32 icon_16x16@2x.png
_make_icon 32 icon_32x32.png
_make_icon 64 icon_32x32@2x.png
_make_icon 128 icon_128x128.png
_make_icon 256 icon_128x128@2x.png
_make_icon 256 icon_256x256.png
_make_icon 512 icon_256x256@2x.png
_make_icon 512 icon_512x512.png
_make_icon 1024 icon_512x512@2x.png

mkdir -p "$APP_BUNDLE/Contents/MacOS" "$APP_BUNDLE/Contents/Resources"
iconutil -c icns "$ICONSET_DIR" -o "$APP_BUNDLE/Contents/Resources/VetStats.icns"

cat >"$APP_BUNDLE/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleDevelopmentRegion</key>
  <string>pl</string>
  <key>CFBundleExecutable</key>
  <string>vetstats</string>
  <key>CFBundleIconFile</key>
  <string>VetStats</string>
  <key>CFBundleIdentifier</key>
  <string>$BUNDLE_ID</string>
  <key>CFBundleInfoDictionaryVersion</key>
  <string>6.0</string>
  <key>CFBundleName</key>
  <string>$APP_NAME</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleShortVersionString</key>
  <string>2.0</string>
  <key>CFBundleVersion</key>
  <string>1</string>
  <key>LSMinimumSystemVersion</key>
  <string>12.0</string>
  <key>NSHighResolutionCapable</key>
  <true/>
</dict>
</plist>
PLIST

cp "$LAUNCHER_SRC" "$APP_BUNDLE/Contents/MacOS/vetstats"
chmod +x "$APP_BUNDLE/Contents/MacOS/vetstats"

echo "Instalowanie skrótu na Pulpicie:"
echo "  $DESKTOP_LINK"

if [[ -e "$DESKTOP_LINK" || -L "$DESKTOP_LINK" ]]; then
  rm -rf "$DESKTOP_LINK"
fi

ln -s "$APP_BUNDLE" "$DESKTOP_LINK"

echo ""
echo "Gotowe."
echo "Uruchom VetStats dwukrotnie klikając:"
echo "  $DESKTOP_LINK"
echo ""
echo "Aplikacja zawsze używa środowiska:"
echo "  $ROOT/.venv"
