#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
DIST="$ROOT/dists/stable"
INDEX_DIR="$DIST/main/binary-iphoneos-arm64"
PACKAGES="$INDEX_DIR/Packages"
RELEASE="$DIST/Release"

command -v dpkg-scanpackages >/dev/null || { echo "缺少 dpkg-scanpackages（请安装 dpkg-dev）" >&2; exit 1; }
command -v gzip >/dev/null
command -v xz >/dev/null

mkdir -p "$INDEX_DIR" pool/main
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

dpkg-scanpackages --multiversion --arch iphoneos-arm64 pool/main /dev/null > "$TMP"
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
  for algo in md5 sha1 sha256 sha512; do
    case "$algo" in
      md5) echo "MD5Sum:"; cmd=md5sum ;;
      sha1) echo "SHA1:"; cmd=sha1sum ;;
      sha256) echo "SHA256:"; cmd=sha256sum ;;
      sha512) echo "SHA512:"; cmd=sha512sum ;;
    esac
    for f in "$PACKAGES" "$PACKAGES.gz" "$PACKAGES.xz"; do
      printf " %s %s main/binary-iphoneos-arm64/%s\n" "$($cmd "$f" | cut -d' ' -f1)" "$(wc -c < "$f" | tr -d ' ')" "$(basename "$f")"
    done
  done
} > "$RELEASE"

echo "APT 索引已生成：$INDEX_DIR"
echo "请将 .deb 放入 pool/main/，再运行本脚本并提交全部变更。"
