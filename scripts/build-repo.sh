#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
command -v dpkg-scanpackages >/dev/null || { echo "dpkg-scanpackages is required (install dpkg-dev)." >&2; exit 1; }
command -v gzip >/dev/null || { echo "gzip is required." >&2; exit 1; }

# Keep the flat root index for package managers that add this URL as "./".
# Also publish canonical Debian APT distribution indexes for stable/main.
dpkg-scanpackages --multiversion debs /dev/null > Packages
gzip -n -9 -c Packages > Packages.gz

python3 - <<'PY'
from pathlib import Path
import gzip, re

raw = Path("Packages").read_bytes()
stanzas = [s for s in re.split(rb"\n\s*\n", raw.strip()) if s.strip()]
arches = (b"iphoneos-arm64", b"iphoneos-arm64e")
for arch_bytes in arches:
    arch = arch_bytes.decode("ascii")
    selected = []
    for stanza in stanzas:
        fields = dict(re.findall(rb"^([A-Za-z0-9-]+):\s*(.*)$", stanza, re.M))
        if fields.get(b"Architecture") == arch_bytes:
            selected.append(stanza.strip())
    if not selected:
        raise SystemExit(f"No packages found for {arch}")
    directory = Path("dists/stable/main") / f"binary-{arch}"
    directory.mkdir(parents=True, exist_ok=True)
    data = b"\n\n".join(selected) + b"\n"
    (directory / "Packages").write_bytes(data)
    with (directory / "Packages.gz").open("wb") as f:
        with gzip.GzipFile(filename="", mode="wb", fileobj=f, compresslevel=9, mtime=0) as gz:
            gz.write(data)
PY

write_release() {
  target="$1"
  shift
  {
    echo "Origin: Oliixwxiilo"
    echo "Label: 丑象派"
    echo "Suite: stable"
    echo "Codename: iphoneos"
    echo "Architectures: iphoneos-arm64 iphoneos-arm64e"
    echo "Components: main"
    echo "Description: Rootless and RootHide personal jailbreak repository"
    echo
    echo "MD5Sum:"
    for f in "$@"; do md5sum "$f" | awk '{printf " %s %s\n", $1, $2}'; done
    echo
    echo "SHA256:"
    for f in "$@"; do sha256sum "$f" | awk '{printf " %s %s\n", $1, $2}'; done
  } > "$target"
}

# Flat-repository metadata (root URL / "./" source entries).
write_release Release Packages Packages.gz

# Standard APT metadata (stable main source entries).
standard_files=()
for arch in iphoneos-arm64 iphoneos-arm64e; do
  standard_files+=("main/binary-$arch/Packages" "main/binary-$arch/Packages.gz")
done
(
  cd dists/stable
  {
    echo "Origin: Oliixwxiilo"
    echo "Label: 丑象派"
    echo "Suite: stable"
    echo "Codename: iphoneos"
    echo "Architectures: iphoneos-arm64 iphoneos-arm64e"
    echo "Components: main"
    echo "Description: Rootless and RootHide personal jailbreak repository"
    echo
    echo "MD5Sum:"
    for f in "${standard_files[@]}"; do md5sum "$f" | awk '{printf " %s %s\n", $1, $2}'; done
    echo
    echo "SHA256:"
    for f in "${standard_files[@]}"; do sha256sum "$f" | awk '{printf " %s %s\n", $1, $2}'; done
  } > Release
)

python3 scripts/audit-debs.py
python3 scripts/audit-dependencies.py
echo "Generated flat and standard APT indexes without modifying DEB packages."
