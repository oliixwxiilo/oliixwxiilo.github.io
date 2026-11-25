#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST="$ROOT/dists/stable"
INDEX_DIR="$DIST/main/binary-iphoneos-arm64"
POOL="$ROOT/pool/main"
PACKAGES="$INDEX_DIR/Packages"
RELEASE="$DIST/Release"

command -v dpkg-scanpackages >/dev/null || { echo "缺少 dpkg-scanpackages（请安装 dpkg-dev）" >&2; exit 1; }
command -v gzip >/dev/null
command -v xz >/dev/null

mkdir -p "$INDEX_DIR" "$POOL"
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

dpkg-scanpackages --multiversion --arch iphoneos-arm64 "$POOL" /dev/null > "$TMP"
install -m 0644 "$TMP" "$PACKAGES"
gzip -9n -c "$PACKAGES" > "$PACKAGES.gz"
xz -9e --threads=1 -c "$PACKAGES" > "$PACKAGES.xz"

{
  echo "Origin: oliixwxiilo Repo"
  echo "Label: oliixwxiilo Repo"
  echo "Suite: stable"
  echo "Codename: stable"
  echo "Architectures: iphoneos-arm64"
  echo "Components: main"
  echo "Description: Rootless iOS package repository"
  echo "Date: $(LC_ALL=C date -Ru)"
  echo "MD5Sum:"
  for f in "$PACKAGES" "$PACKAGES.gz" "$PACKAGES.xz"; do
    printf " %s %s main/binary-iphoneos-arm64/%s\n" "$(md5sum "$f" | cut -d' ' -f1)" "$(wc -c < "$f" | tr -d ' ')" "$(basename "$f")"
  done
  echo "SHA1:"
  for f in "$PACKAGES" "$PACKAGES.gz" "$PACKAGES.xz"; do
    printf " %s %s main/binary-iphoneos-arm64/%s\n" "$(sha1sum "$f" | cut -d' ' -f1)" "$(wc -c < "$f" | tr -d ' ')" "$(basename "$f")"
  done
  echo "SHA256:"
  for f in "$PACKAGES" "$PACKAGES.gz" "$PACKAGES.xz"; do
    printf " %s %s main/binary-iphoneos-arm64/%s\n" "$(sha256sum "$f" | cut -d' ' -f1)" "$(wc -c < "$f" | tr -d ' ')" "$(basename "$f")"
  done
  echo "SHA512:"
  for f in "$PACKAGES" "$PACKAGES.gz" "$PACKAGES.xz"; do
    printf " %s %s main/binary-iphoneos-arm64/%s\n" "$(sha512sum "$f" | cut -d' ' -f1)" "$(wc -c < "$f" | tr -d ' ')" "$(basename "$f")"
  done
} > "$RELEASE"

echo "APT 索引已生成：$INDEX_DIR"
echo "请将 .deb 放入 pool/main/，再运行本脚本并提交全部变更。"
