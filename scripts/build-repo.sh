#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
command -v dpkg-scanpackages >/dev/null || { echo "dpkg-scanpackages is required (install dpkg-dev)." >&2; exit 1; }
# Keep the existing package paths stable during the first migration phase.
dpkg-scanpackages --multiversion . /dev/null > Packages
gzip -n -9 -c Packages > Packages.gz
{
  echo "Origin: Oliixwxiilo"
  echo "Label: 丑象派"
  echo "Suite: stable"
  echo "Codename: iphoneos"
  echo "Architectures: iphoneos-arm64 iphoneos-arm64e"
  echo "Components: main"
  echo "Description: Rootless and RootHide personal jailbreak repository"
  echo "Date: $(LC_ALL=C date -Ru)"
  echo
  echo "MD5Sum:"
  md5sum Packages Packages.gz | awk '{printf " %s %s\n", $1, $2}'
  echo
  echo "SHA256:"
  sha256sum Packages Packages.gz | awk '{printf " %s %s\n", $1, $2}'
} > Release
python3 scripts/audit-debs.py
python3 scripts/generate-catalog.py
echo "Repository indexes and package catalog generated."
