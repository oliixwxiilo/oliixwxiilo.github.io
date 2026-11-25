#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
for f in Packages Packages.gz Release dists/stable/Release; do
  test -s "$f" || { echo "Missing or empty: $f" >&2; exit 1; }
done
python3 - <<'PY'
from pathlib import Path
import gzip, hashlib, json, re

def stanzas(path):
    raw = path.read_text(encoding="utf-8", errors="replace")
    return [s for s in re.split(r"\n\s*\n", raw.strip()) if s.strip()]

root = stanzas(Path("Packages"))
if not root:
    raise SystemExit("Root Packages index has no entries")
seen = set()
for stanza in root:
    f = dict(re.findall(r"^([A-Za-z0-9-]+):\s*(.*)$", stanza, re.M))
    for k in ("Package", "Version", "Architecture", "Filename", "Size", "SHA256"):
        if k not in f:
            raise SystemExit("Missing " + k + " in package stanza")
    key = (f["Package"], f["Version"], f["Architecture"])
    if key in seen:
        raise SystemExit("Duplicate package identity: " + repr(key))
    seen.add(key)
    p = Path(f["Filename"].removeprefix("./"))
    if p.is_absolute() or ".." in p.parts or len(p.parts) != 3 or p.parts[0] != "debs" or p.parts[1] not in ("rootless", "roothide") or not p.is_file():
        raise SystemExit("Missing or unsafe DEB path: " + str(p))
    if hashlib.sha256(p.read_bytes()).hexdigest() != f["SHA256"].lower():
        raise SystemExit("DEB SHA256 mismatch: " + str(p))
    if p.stat().st_size != int(f["Size"]):
        raise SystemExit("DEB size mismatch: " + str(p))

audit = json.loads(Path(".github/audit/package-audit.json").read_text())
deps = json.loads(Path(".github/audit/dependency-audit.json").read_text())
if len(audit.get("packages", [])) != len(root):
    raise SystemExit("DEB audit count mismatch")
if len(deps.get("packages", [])) != len(root):
    raise SystemExit("Dependency audit count mismatch")

def check_release(release_path, expected_files):
    release = release_path.read_text()
    def val(k):
        m = re.search(r"^" + re.escape(k) + r":\s*(.*)$", release, re.M)
        return m.group(1).strip() if m else ""
    if val("Suite") != "stable" or val("Codename") != "iphoneos" or val("Components") != "main":
        raise SystemExit("Unexpected Release metadata: " + str(release_path))
    if not {"iphoneos-arm64", "iphoneos-arm64e"}.issubset(set(val("Architectures").split())):
        raise SystemExit("Missing architectures: " + str(release_path))
    base = release_path.parent
    for section, algo in (("MD5Sum", "md5"), ("SHA256", "sha256")):
        m = re.search(r"(?m)^" + section + r":\n((?:[ \t].*\n?)*)", release)
        entries = {}
        for line in (m.group(1).splitlines() if m else []):
            a = line.split()
            if len(a) == 3:
                entries[a[2]] = a[0].lower()
        if set(entries) != set(expected_files):
            raise SystemExit(section + " paths mismatch in " + str(release_path) + ": " + repr(set(entries)))
        for name in expected_files:
            p = base / name
            if not p.is_file():
                raise SystemExit("Missing indexed file: " + str(p))
            if hashlib.new(algo, p.read_bytes()).hexdigest() != entries[name]:
                raise SystemExit(section + " checksum mismatch: " + str(p))

check_release(Path("Release"), ["Packages", "Packages.gz"])
check_release(Path("dists/stable/Release"), [
    f"main/binary-{arch}/{index}"
    for arch in ("iphoneos-arm64", "iphoneos-arm64e")
    for index in ("Packages", "Packages.gz")
])
if gzip.decompress(Path("Packages.gz").read_bytes()) != Path("Packages").read_bytes():
    raise SystemExit("Root Packages.gz does not match Packages")

for arch in ("iphoneos-arm64", "iphoneos-arm64e"):
    path = Path("dists/stable/main") / f"binary-{arch}"
    entries = stanzas(path / "Packages")
    if not entries:
        raise SystemExit("Empty standard index for " + arch)
    for stanza in entries:
        f = dict(re.findall(r"^([A-Za-z0-9-]+):\s*(.*)$", stanza, re.M))
        if f.get("Architecture") != arch:
            raise SystemExit("Wrong architecture in " + str(path))
    if gzip.decompress((path / "Packages.gz").read_bytes()) != (path / "Packages").read_bytes():
        raise SystemExit("Compressed index mismatch for " + arch)
    if len(entries) != sum(1 for s in root if dict(re.findall(r"^([A-Za-z0-9-]+):\s*(.*)$", s, re.M)).get("Architecture") == arch):
        raise SystemExit("Package count mismatch for " + arch)

print(f"Validated {len(root)} packages, both APT layouts, all DEB hashes and all Release checksums.")
PY
