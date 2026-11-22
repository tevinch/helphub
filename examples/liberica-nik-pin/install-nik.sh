#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  printf 'Usage: bash install-nik.sh NEW_DIRECTORY [LOCAL_ARCHIVE]\n' >&2
  exit 2
fi

destination="$1"
if [[ -e "$destination" || -L "$destination" ]]; then
  printf 'Choose a new installation directory: %s\n' "$destination" >&2
  exit 2
fi

case "$(uname -s):$(uname -m)" in
  Darwin:arm64)
    platform=macos-aarch64
    checksum=2e7c04e54d94f367e3dadce3df4984d75273e6089c5e09aeae38a4868bd6eb54
    home_path=Contents/Home
    ;;
  Linux:aarch64)
    platform=linux-aarch64
    checksum=ac01657375e09552e26344e1b90068ad21161cc50cd4dc6d578e2dbf2894e843
    home_path=.
    ;;
  *)
    printf 'Use this example on Apple Silicon macOS or glibc Linux ARM64.\n' >&2
    exit 2
    ;;
esac

if [[ $# -eq 2 ]]; then
  archive="$2"
else
  scratch="$(mktemp -d)"
  trap 'rm -rf "$scratch"' EXIT
  archive="$scratch/nik.tar.gz"
  base_url='https://github.com/bell-sw/LibericaNIK/releases/download/jdk-25.0.5.0.3%2B6'
  asset="bellsoft-liberica-vm-openjdk25.0.5.0.3+6-25.0.5.0.3+1-${platform}.tar.gz"
  curl --fail --location --silent --show-error --output "$archive" "$base_url/$asset"
fi

if command -v sha256sum >/dev/null 2>&1; then
  digest="$(sha256sum < "$archive")"
else
  digest="$(shasum -a 256 < "$archive")"
fi
if [[ "${digest%% *}" != "$checksum" ]]; then
  printf 'SHA-256 mismatch for the %s archive.\n' "$platform" >&2
  exit 1
fi

mkdir -- "$destination"
tar -xzf "$archive" -C "$destination" --strip-components=1
java_home="$(cd "$destination/$home_path" && pwd -P)"
test -x "$java_home/bin/java"
test -x "$java_home/bin/native-image"
printf '%s\n' "$java_home"
