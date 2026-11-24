#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
for f in Packages Release; do test -s "$f" || { echo "Missing or empty: $f" >&2; exit 1; }; done
python3 - <<'PY'
from pathlib import Path
import hashlib,json,re
raw=Path("Packages").read_text(encoding="utf-8",errors="replace")
stanzas=[s for s in re.split(r"\n\s*\n",raw.strip()) if s.strip()]
if not stanzas: raise SystemExit("Packages index has no entries")
seen=set()
for stanza in stanzas:
    f=dict(re.findall(r"^([A-Za-z0-9-]+):\s*(.*)$",stanza,re.M))
    for k in ("Package","Version","Architecture","Filename","Size","SHA256"):
        if k not in f: raise SystemExit("Missing "+k+" in package stanza")
    key=(f["Package"],f["Version"],f["Architecture"])
    if key in seen: raise SystemExit("Duplicate package identity: "+repr(key))
    seen.add(key)
    p=Path(f["Filename"].removeprefix("./"))
    if p.is_absolute() or ".." in p.parts or len(p.parts)!=3 or p.parts[0]!="debs" or p.parts[1] not in ("rootless","roothide") or not p.is_file():
        raise SystemExit("Missing or unsafe DEB path: "+str(p))
    if hashlib.sha256(p.read_bytes()).hexdigest()!=f["SHA256"].lower(): raise SystemExit("DEB SHA256 mismatch: "+str(p))
    if p.stat().st_size!=int(f["Size"]): raise SystemExit("DEB size mismatch: "+str(p))
audit=json.loads(Path(".github/audit/package-audit.json").read_text())
if len(audit.get("packages",[]))!=len(stanzas): raise SystemExit("DEB audit count mismatch")
deps=json.loads(Path(".github/audit/dependency-audit.json").read_text())
if len(deps.get("packages",[]))!=len(stanzas): raise SystemExit("Dependency audit count mismatch")
release=Path("Release").read_text()
def val(k):
    m=re.search(r"^"+re.escape(k)+r":\s*(.*)$",release,re.M); return m.group(1).strip() if m else ""
if val("Suite")!="stable" or val("Codename")!="iphoneos" or val("Components")!="main": raise SystemExit("Unexpected Release metadata")
if not {"iphoneos-arm64","iphoneos-arm64e"}.issubset(set(val("Architectures").split())): raise SystemExit("Missing architectures")
for section,algo in (("MD5Sum","md5"),("SHA256","sha256")):
    m=re.search(r"(?m)^"+section+r":\n((?:[ \t].*\n?)*)",release)
    entries={}
    for line in (m.group(1).splitlines() if m else []):
        a=line.split()
        if len(a)==2: entries[a[1]]=a[0].lower()
    if set(entries)!={"Packages"}: raise SystemExit(section+" must list only Packages")
    if hashlib.new(algo,Path("Packages").read_bytes()).hexdigest()!=entries["Packages"]: raise SystemExit(section+" checksum mismatch")
print("Validated "+str(len(stanzas))+" APT packages, DEB hashes, audits and Release checksums.")
PY
